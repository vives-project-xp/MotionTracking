import pygame
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import math
import sys
import multiprocessing
import ctypes
from ultralytics import YOLO
import os

# --- CONFIGURATIE ---
CAMERA_INDEX = 0
CAMERA_RES = (640, 480)
SMOOTHING = 0.25             # Iets hoger gezet voor minder delay bij meerdere personen
ARUCO_DICT = aruco.DICT_4X4_50
REQUIRED_STABLE_TIME = 2 

# Kleuren
ZWART = (0, 0, 0)
WIT = (255, 255, 255)
NEON_GEEL = (255, 255, 0)
NEON_BLAUW = (0, 255, 255)
ROOD = (255, 0, 0)

# --- PROCES 1: TRACKER (Camera + AI) ---
def run_tracker(shared_queue, stop_event, is_calibrated_flag):
    # Gebruik een lichtere imgsz voor minder delay op de Pi
    model = YOLO('yolov8n.pt')

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RES[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RES[1])
    cap.set(cv2.CAP_PROP_FPS, 30)

    aruco_dict_obj = aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict_obj, parameters)

    fixed_pts = None
    transform_matrix = None
    start_lock_time = None
    local_locked = False

    print("[TRACKER] Camera gestart. Zoeken naar projectie...")

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        if not local_locked:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            points = {}
            if ids is not None:
                for i in range(len(ids)):
                    points[ids[i][0]] = corners[i][0]

                if all(id in points for id in [0, 1, 2, 3]):
                    if start_lock_time is None:
                        start_lock_time = time.time()
                    
                    elapsed = time.time() - start_lock_time
                    tl, tr, br, bl = points[0][0], points[1][1], points[3][2], points[2][3]
                    temp_pts = np.array([tl, tr, br, bl], np.float32)

                    if elapsed >= REQUIRED_STABLE_TIME:
                        fixed_pts = temp_pts
                        src_pts = fixed_pts.reshape(4, 2).astype(np.float32)
                        dst_pts = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=np.float32)
                        transform_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                        local_locked = True
                        is_calibrated_flag.value = 1
                        print("[TRACKER] Gebied vergrendeld! Start Multi-Tracking.")
                else:
                    start_lock_time = None
        else:
            # GEBRUIK .track VOOR MEERDERE PERSONEN MET ID's
            results = model.track(frame, persist=True, verbose=False, classes=[0], imgsz=160, tracker="botsort.yaml")
            
            tracked_people = {} # Dictionary: { id: (kx, ky) }

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                ids = results[0].boxes.id.cpu().numpy().astype(int)

                for box, obj_id in zip(boxes, ids):
                    x1, y1, x2, y2 = box
                    center_x = int((x1 + x2) / 2)
                    center_y = int(y1 + (y2 - y1) * 0.3)

                    poly_pts = fixed_pts.reshape((-1, 1, 2)).astype(np.int32)
                    if cv2.pointPolygonTest(poly_pts, (float(center_x), float(center_y)), False) >= 0:
                        p = np.array([[[center_x, center_y]]], dtype=np.float32)
                        tp = cv2.perspectiveTransform(p, transform_matrix)[0][0]
                        kx, ky = np.clip(tp[0], 0.0, 1.0), np.clip(tp[1], 0.0, 1.0)
                        
                        tracked_people[obj_id] = (float(kx), float(ky))

            # Stuur de hele groep mensen door naar de visualizer
            try:
                shared_queue.put(tracked_people, block=False)
            except:
                pass

    cap.release()

def draw_dynamic_arrow(surface, color, start, end, thickness=10):
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist < 40: return
    angle = math.atan2(dy, dx)
    pygame.draw.line(surface, color, start, end, thickness)
    head_size = 40 + (dist * 0.02)
    p1 = (end[0] - head_size * math.cos(angle - 0.5), end[1] - head_size * math.sin(angle - 0.5))
    p2 = (end[0] - head_size * math.cos(angle + 0.5), end[1] - head_size * math.sin(angle + 0.5))
    pygame.draw.polygon(surface, color, [end, p1, p2])

def run_visualizer(shared_queue, stop_event, is_calibrated_flag):
    pygame.init()
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    MARKER_SIZE, MARGIN = 200, 50
    MARKER_DIR = "Markers" 

    try:
        m = [pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, f"marker{i}.png")), (MARKER_SIZE, MARKER_SIZE)) for i in range(4)]
    except:
        m = [pygame.Surface((MARKER_SIZE, MARKER_SIZE)) for _ in range(4)]
        for surf in m: surf.fill(ROOD)

    # Dictionary om de huidige soepele posities per ID vast te houden
    # { id: [current_x, current_y] }
    smooth_positions = {}

    print("[VISUALIZER] Wachten op kalibratie...")

    while not stop_event.is_set():
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: stop_event.set()

        if is_calibrated_flag.value == 0:
            screen.fill(WIT)
            screen.blit(m[0], (MARGIN, MARGIN))
            screen.blit(m[1], (WIDTH - MARKER_SIZE - MARGIN, MARGIN))
            screen.blit(m[2], (MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            screen.blit(m[3], (WIDTH - MARKER_SIZE - MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            pygame.display.flip()
        else:
            # Data ophalen (de nieuwste dictionary met alle mensen)
            new_data = None
            try:
                while not shared_queue.empty():
                    new_data = shared_queue.get_nowait()
            except: pass

            screen.fill(ZWART)

            if new_data:
                # Update posities voor actieve ID's
                active_ids = list(new_data.keys())
                
                for obj_id, (kx, ky) in new_data.items():
                    target_x, target_y = kx * WIDTH, ky * HEIGHT
                    
                    if obj_id not in smooth_positions:
                        smooth_positions[obj_id] = [target_x, target_y]
                    else:
                        # Bereken smoothing voor dit specifieke ID
                        smooth_positions[obj_id][0] += (target_x - smooth_positions[obj_id][0]) * SMOOTHING
                        smooth_positions[obj_id][1] += (target_y - smooth_positions[obj_id][1]) * SMOOTHING

                # Verwijder ID's die niet meer in beeld zijn (optioneel, voor opschoning)
                # In een echte installatie zou je een timeout kunnen toevoegen
                current_ids = list(smooth_positions.keys())
                for cid in current_ids:
                    if cid not in active_ids:
                        del smooth_positions[cid]

            # Teken alle actieve pijlen
            for obj_id, pos in smooth_positions.items():
                curr_x, curr_y = int(pos[0]), int(pos[1])
                draw_dynamic_arrow(screen, NEON_GEEL, (WIDTH//2, HEIGHT//2), (curr_x, curr_y))
                pygame.draw.circle(screen, NEON_BLAUW, (curr_x, curr_y), 20, 3)
                pygame.draw.circle(screen, NEON_GEEL, (curr_x, curr_y), 8)

            pygame.display.flip()
        
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    coords_queue = multiprocessing.Queue(maxsize=10)
    stop_signal = multiprocessing.Event()
    is_calibrated = multiprocessing.Value('i', 0)

    tracker_process = multiprocessing.Process(target=run_tracker, args=(coords_queue, stop_signal, is_calibrated))
    tracker_process.start()

    try:
        run_visualizer(coords_queue, stop_signal, is_calibrated)
    except KeyboardInterrupt:
        stop_signal.set()
    finally:
        tracker_process.join()
        print("Systeem succesvol afgesloten.")