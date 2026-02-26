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
SMOOTHING = 0.1
ARUCO_DICT = aruco.DICT_4X4_50
REQUIRED_STABLE_TIME = 2      # Seconden dat marker stabiel moet zijn

# Kleuren
ZWART = (0, 0, 0)
WIT = (255, 255, 255)
NEON_GEEL = (255, 255, 0)
NEON_BLAUW = (0, 255, 255)
ROOD = (255, 0, 0)

# --- PROCES 1: TRACKER (Camera + AI) ---
def run_tracker(shared_queue, stop_event, is_calibrated_flag):
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
                        print("[TRACKER] Markers gezien... stabiliseren...")

                    elapsed = time.time() - start_lock_time

                    tl = points[0][0]
                    tr = points[1][1]
                    br = points[3][2]
                    bl = points[2][3]

                    temp_pts = np.array([tl, tr, br, bl], np.float32)

                    if elapsed >= REQUIRED_STABLE_TIME:
                        fixed_pts = temp_pts
                        src_pts = fixed_pts.reshape(4, 2).astype(np.float32)
                        dst_pts = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=np.float32)
                        transform_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                        local_locked = True
                        is_calibrated_flag.value = 1
                        print("[TRACKER] Gebied vergrendeld! Start YOLO.")
                else:
                    start_lock_time = None
        else:
            results = model(frame, verbose=False, classes=[0], imgsz=320, stream=True)
            detected = False
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center_x = int((x1 + x2) / 2)
                    center_y = int(y1 + (y2 - y1) * 0.3)

                    poly_pts = fixed_pts.reshape((-1, 1, 2)).astype(np.int32)
                    if cv2.pointPolygonTest(poly_pts, (float(center_x), float(center_y)), False) >= 0:
                        p = np.array([[[center_x, center_y]]], dtype=np.float32)
                        tp = cv2.perspectiveTransform(p, transform_matrix)[0][0]
                        kx = np.clip(tp[0], 0.0, 1.0)
                        ky = np.clip(tp[1], 0.0, 1.0)
                        try:
                            shared_queue.put((float(kx), float(ky)), block=False)
                        except:
                            pass
                        detected = True
                        break
                if detected: break

    cap.release()

def draw_dynamic_arrow(surface, color, start, end, thickness=10):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
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

    MARKER_SIZE = 200
    MARGIN = 50
    MARKER_DIR = "Markers" # <--- De mapnaam

    # --- MARKERS LADEN UIT SUBMAP ---
    try:
        m0 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker0.png")), (MARKER_SIZE, MARKER_SIZE))
        m1 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker1.png")), (MARKER_SIZE, MARKER_SIZE))
        m2 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker2.png")), (MARKER_SIZE, MARKER_SIZE))
        m3 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker3.png")), (MARKER_SIZE, MARKER_SIZE))
    except Exception as e:
        print(f"WAARSCHUWING: Marker plaatjes niet gevonden in '{MARKER_DIR}'! {e}")
        m0 = m1 = m2 = m3 = pygame.Surface((MARKER_SIZE, MARKER_SIZE))
        m0.fill(ROOD)

    current_x, current_y = WIDTH / 2, HEIGHT / 2
    target_x, target_y = WIDTH / 2, HEIGHT / 2

    print("[VISUALIZER] Wachten op kalibratie...")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

        if is_calibrated_flag.value == 0:
            screen.fill(WIT)
            screen.blit(m0, (MARGIN, MARGIN))
            screen.blit(m1, (WIDTH - MARKER_SIZE - MARGIN, MARGIN))
            screen.blit(m2, (MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            screen.blit(m3, (WIDTH - MARKER_SIZE - MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            font = pygame.font.SysFont(None, 40)
            text = font.render("Kalibratie: Zorg dat de camera alle markers ziet...", True, ZWART)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))
        else:
            try:
                new_pos = None
                while not shared_queue.empty():
                    new_pos = shared_queue.get_nowait()
                if new_pos:
                    target_x = new_pos[0] * WIDTH
                    target_y = new_pos[1] * HEIGHT
            except: pass

            current_x += (target_x - current_x) * SMOOTHING
            current_y += (target_y - current_y) * SMOOTHING

            screen.fill(ZWART)
            draw_dynamic_arrow(screen, NEON_GEEL, (WIDTH//2, HEIGHT//2), (int(current_x), int(current_y)))
            pygame.draw.circle(screen, NEON_BLAUW, (int(current_x), int(current_y)), 20, 3)
            pygame.draw.circle(screen, NEON_GEEL, (int(current_x), int(current_y)), 8)

        pygame.display.flip()
        clock.tick(60)

    stop_event.set()
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