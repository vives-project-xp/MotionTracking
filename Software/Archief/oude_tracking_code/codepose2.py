import pygame
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import math
import multiprocessing
import random
from ultralytics import YOLO
import requests

# --- 1. CONFIGURATIE ---
VM_IP = "10.20.10.18"
ACTIVE_MODE = "FIRE"
CAMERA_INDEX = 0
CAMERA_RES = (640, 480)
ARUCO_DICT = aruco.DICT_4X4_50
REQUIRED_STABLE_TIME = 1.0
ZWART = (0, 0, 0)
WIT = (255, 255, 255)
ROOD = (255, 0, 0)

# --- 2. EFFECTEN ---
EFFECTS = {
    "MAGIC": {"colors": [(150, 50, 255), (100, 200, 255)], "gravity": 0.0, "decay": (4, 10), "size": (3, 8), "spawn": 8, "trail": 40},
    "FIRE": {"colors": [(255, 60, 0), (255, 150, 0), (255, 230, 50)], "gravity": -0.3, "decay": (8, 15), "size": (4, 10), "spawn": 15, "trail": 60},
    "CYBER": {"colors": [(0, 255, 150), (0, 255, 255)], "gravity": 0.0, "decay": (15, 25), "size": (2, 5), "spawn": 20, "trail": 20},
    "GHOST": {"colors": [(200, 200, 255), (255, 255, 255)], "gravity": 0.02, "decay": (2, 5), "size": (2, 4), "spawn": 4, "trail": 10}
}

# --- 3. TRACKER (YOLO Pose - Multiplayer Support) ---
def run_tracker(shared_queue, stop_event, is_calibrated_flag):
    model = YOLO('yolov8n-pose.pt')
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RES[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RES[1])

    aruco_det = aruco.ArucoDetector(aruco.getPredefinedDictionary(ARUCO_DICT))
    fixed_pts, transform_matrix, start_lock_time = None, None, None
    local_locked = False

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret: continue

        if not local_locked:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = aruco_det.detectMarkers(gray)
            if ids is not None and len(ids) >= 4:
                points = {ids[i][0]: corners[i][0] for i in range(len(ids))}
                if all(id in points for id in [0, 1, 2, 3]):
                    if start_lock_time is None: start_lock_time = time.time()
                    if time.time() - start_lock_time >= REQUIRED_STABLE_TIME:
                        tl, tr, br, bl = points[0][0], points[1][1], points[3][2], points[2][3]
                        fixed_pts = np.array([tl, tr, br, bl], np.float32)
                        dst_pts = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=np.float32)
                        transform_matrix = cv2.getPerspectiveTransform(fixed_pts, dst_pts)
                        local_locked, is_calibrated_flag.value = True, 1
            else: start_lock_time = None
        else:
            results = model(frame, verbose=False, imgsz=160, stream=True) # Hogere imgsz helpt bij meer mensen
            all_people_data = []

            for r in results:
                if r.keypoints and len(r.keypoints.xy) > 0:
                    # Loop door ELKE gedetecteerde persoon
                    for person_kpts in r.keypoints.xy.cpu().numpy():
                        if len(person_kpts) > 10:
                            nose, l_hand, r_hand = person_kpts[0], person_kpts[9], person_kpts[10]

                            # Check of persoon binnen ArUco veld staat
                            if cv2.pointPolygonTest(fixed_pts.astype(np.int32), (float(nose[0]), float(nose[1])), False) >= 0:
                                tp = cv2.perspectiveTransform(np.array([[[nose[0], nose[1]]]], dtype=np.float32), transform_matrix)[0][0]

                                person_dict = {"body": (float(tp[0]), float(tp[1])), "hands": []}

                                for hand in [l_hand, r_hand]:
                                    if hand[0] > 0: # Check of hand gedetecteerd is
                                        tp_h = cv2.perspectiveTransform(np.array([[[hand[0], hand[1]]]], dtype=np.float32), transform_matrix)[0][0]
                                        person_dict["hands"].append((float(tp_h[0]), float(tp_h[1])))

                                all_people_data.append(person_dict)

            if all_people_data and not shared_queue.full():
                shared_queue.put(all_people_data, block=False)

    cap.release()

# --- 4. DEELTJES ---
class Particle:
    def __init__(self, x, y, cfg, is_hand=False):
        self.x, self.y = x, y
        self.cfg = cfg
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-1.5, 1.5)
        if is_hand: self.vy -= 1.5
        self.life, self.color = 255, random.choice(cfg["colors"])
        self.decay = random.randint(*cfg["decay"])
        self.size = random.randint(*cfg["size"])

    def update(self):
        self.vy += self.cfg["gravity"]
        self.x += self.vx; self.y += self.vy
        self.life -= self.decay; self.size -= 0.05

    def draw(self, surf):
        if self.life > 0 and self.size > 0:
            f = self.life / 255.0
            c = (int(self.color[0]*f), int(self.color[1]*f), int(self.color[2]*f))
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), max(1, int(self.size)))

# --- 5. VISUALIZER (Multiplayer Ready) ---
def run_visualizer(shared_queue, stop_event, is_calibrated_flag):
    pygame.init()
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    marker_imgs = []
    for i in range(4):
        try:
            img = pygame.image.load(f"Markers/marker{i}.png")
            marker_imgs.append(pygame.transform.scale(img, (200, 200)))
        except:
            s = pygame.Surface((200, 200)); s.fill(ROOD); marker_imgs.append(s)

    current_mode = ACTIVE_MODE
    cfg = EFFECTS[current_mode].copy()
    cfg.update({'offset_px': 80, 'spawn': 10, 'current_size_val': 5})

    people_list = [] # Bevat de laatste data van alle personen
    particles = []
    trail = pygame.Surface((WIDTH, HEIGHT))
    trail.fill(ZWART)
    frame_count = 0

    while not stop_event.is_set():
        frame_count += 1
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: stop_event.set()

        if is_calibrated_flag.value == 0:
            screen.fill(WIT)
            for i, pos in enumerate([(50, 50), (WIDTH-250, 50), (50, HEIGHT-250), (WIDTH-250, HEIGHT-250)]):
                screen.blit(marker_imgs[i], pos)
            pygame.display.flip()
            continue

        # Config ophalen van VM
        if frame_count % 30 == 0:
            try:
                r = requests.get(f"http://{VM_IP}:5000/get_config", timeout=0.05)
                if r.status_code == 200:
                    data = r.json()
                    cfg = EFFECTS[data['mode']].copy()
                    cfg.update({'current_size_val': int(data['size']), 'spawn': int(data['spawn']), 'offset_px': int(data.get('offset', 80))})
                    cfg['size'] = (cfg['current_size_val'], cfg['current_size_val']+4)
            except: pass

        # Data ophalen uit de queue
        try:
            while not shared_queue.empty():
                people_list = shared_queue.get_nowait()
        except: pass

        # Teken effecten
        trail.set_alpha(cfg["trail"])
        screen.blit(trail, (0,0))

        scale = cfg['current_size_val'] / 5.0

        for person in people_list:
            bx, by = person["body"][0]*WIDTH, person["body"][1]*HEIGHT
            v_y = by - cfg['offset_px']

            # Spawn particles voor hoofd/body
            for _ in range(cfg["spawn"]):
                ang, r = random.uniform(0, 6.28), random.uniform(30, 70) * scale
                particles.append(Particle(bx + math.cos(ang)*r, v_y + math.sin(ang)*r, cfg))

            # Spawn particles voor handen
            for h in person["hands"]:
                hx, hy = h[0]*WIDTH, h[1]*HEIGHT
                for _ in range(3):
                    particles.append(Particle(hx, hy, cfg, is_hand=True))

        # Update en teken alle particles
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(screen)

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    q = multiprocessing.Queue(maxsize=2)
    stop, calib = multiprocessing.Event(), multiprocessing.Value('i', 0)
    p = multiprocessing.Process(target=run_tracker, args=(q, stop, calib))
    p.start()
    try:
        run_visualizer(q, stop, calib)
    finally:
        stop.set()
        p.join()