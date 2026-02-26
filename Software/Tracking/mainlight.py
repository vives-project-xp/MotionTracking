import pygame
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import math
import sys
import multiprocessing
import random
from ultralytics import YOLO
import os

# --- CONFIGURATIE ---
CAMERA_INDEX = 0
CAMERA_RES = (640, 480)
ARUCO_DICT = aruco.DICT_4X4_50
REQUIRED_STABLE_TIME = 2

# Kleuren
ZWART = (0, 0, 0)
WIT = (255, 255, 255)
ROOD = (255, 0, 0)


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
            results = model(frame, verbose=False, classes=[0], imgsz=192, stream=True)
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

# --- KLASSE VOOR DE VISUALS (Aangepast voor "Orbit" effect) ---
class Particle:
    def __init__(self, x, y, velocity_x, velocity_y, speed_intensity):
        self.x = x
        self.y = y
        # Deeltjes bewegen nu rustiger rondom de persoon, niet direct wegvliegend
        # Ze krijgen een lichte draaiing mee
        angle_movement = math.atan2(velocity_y, velocity_x) + random.uniform(-0.5, 0.5)
        speed = random.uniform(1, 3) + (speed_intensity * 0.1)

        self.vx = math.cos(angle_movement) * speed
        self.vy = math.sin(angle_movement) * speed

        self.life = 255
        self.decay = random.randint(4, 10) # Iets snellere decay

        # Kleuren (meer "magisch" palet)
        if speed_intensity > 15: # Rennen = Fel cyaan/wit
            self.size = random.randint(5, 10)
            self.color = (200, 255, 255)
        elif speed_intensity > 5: # Lopen = Paars/Roze
            self.size = random.randint(3, 7)
            self.color = (255, 100, 255)
        else: # Stilstaan = Diep blauw
            self.size = random.randint(2, 5)
            self.color = (50, 100, 255)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        self.size -= 0.05

    def draw(self, surface):
        if self.life > 0 and self.size > 0:
            # Simpele alpha fade
            fade_factor = max(0, min(1, self.life / 255.0))
            r = int(self.color[0] * fade_factor)
            g = int(self.color[1] * fade_factor)
            b = int(self.color[2] * fade_factor)
            pygame.draw.circle(surface, (r, g, b), (int(self.x), int(self.y)), int(self.size))

# --- PROCES 2: VISUALIZER (Aangepast) ---
def run_visualizer(shared_queue, stop_event, is_calibrated_flag):
    pygame.init()
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # --- MARKER LOADING (JOUW CODE) ---
    MARKER_SIZE = 200
    MARGIN = 50
    MARKER_DIR = "Markers"
    try:
        m0 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker0.png")), (MARKER_SIZE, MARKER_SIZE))
        m1 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker1.png")), (MARKER_SIZE, MARKER_SIZE))
        m2 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker2.png")), (MARKER_SIZE, MARKER_SIZE))
        m3 = pygame.transform.scale(pygame.image.load(os.path.join(MARKER_DIR, "marker3.png")), (MARKER_SIZE, MARKER_SIZE))
    except Exception as e:
        print(f"WAARSCHUWING: {e}")
        m0=m1=m2=m3 = pygame.Surface((MARKER_SIZE, MARKER_SIZE)); m0.fill(ROOD)

    # Variabelen Visuals
    current_x, current_y = WIDTH / 2, HEIGHT / 2
    target_x, target_y = WIDTH / 2, HEIGHT / 2
    particles = []

    # Trail surface (iets donkerder voor meer contrast)
    trail_surface = pygame.Surface((WIDTH, HEIGHT))
    trail_surface.set_alpha(40)
    trail_surface.fill(ZWART)

    print("[VISUALIZER] Aura Engine gestart...")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

        # --- MODUS 1: KALIBRATIE ---
        if is_calibrated_flag.value == 0:
            screen.fill(WIT)
            screen.blit(m0, (MARGIN, MARGIN))
            screen.blit(m1, (WIDTH - MARKER_SIZE - MARGIN, MARGIN))
            screen.blit(m2, (MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            screen.blit(m3, (WIDTH - MARKER_SIZE - MARGIN, HEIGHT - MARKER_SIZE - MARGIN))
            font = pygame.font.SysFont(None, 40)
            text = font.render("Kalibratie...", True, ZWART)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))
            pygame.display.flip()
            clock.tick(30)
            continue

        # --- MODUS 2: LIVE VISUALS (AURA/ORBIT) ---

        # 1. Data & Smoothing
        try:
            while not shared_queue.empty():
                pos = shared_queue.get_nowait()
                target_x = pos[0] * WIDTH
                target_y = pos[1] * HEIGHT
        except: pass

        dx = target_x - current_x
        dy = target_y - current_y
        dist = math.hypot(dx, dy)

        # Iets tragere smoothing zodat de aura "achterna" komt
        current_x += dx * 0.15
        current_y += dy * 0.15

        # 2. Fade effect
        screen.blit(trail_surface, (0, 0))

        # 3. Nieuwe deeltjes spawnen RONDOM de persoon
        spawn_count = int(dist) + 3
        if spawn_count > 25: spawn_count = 25

        for _ in range(spawn_count):
            # Bepaal een willekeurige hoek en afstand rond het centrum
            angle = random.uniform(0, 2 * math.pi)
            # De straal van de wolk wordt groter als je sneller beweegt
            radius_cloud = random.uniform(30, 60 + dist*2)

            # Bereken spawn positie met offset
            spawn_x = current_x + math.cos(angle) * radius_cloud
            spawn_y = current_y + math.sin(angle) * radius_cloud

            # Spawn deeltje
            p = Particle(spawn_x, spawn_y, dx, dy, dist)
            particles.append(p)

        # 4. Deeltjes updaten en tekenen
        for p in particles[:]:
            p.update()
            if p.life <= 0 or p.size <= 0:
                particles.remove(p)
            else:
                p.draw(screen)

        # 5. TEKEN DE "FORCEFIELD RINGS" (ipv de centrale stip)
        # Kleur bepalen
        if dist > 5:
            ring_color = (200, 255, 255) # Fel cyaan bij beweging
        else:
            ring_color = (50, 100, 255) # Diep blauw bij stilstand

        # Pulserend effect voor de ringen
        pulse1 = math.sin(time.time() * 4) * 5
        pulse2 = math.cos(time.time() * 3) * 5

        # Teken 2 dunne ringen die om de persoon draaien
        # De 'width' parameter (laatste getal) zorgt dat het een ring is en geen cirkel
        pygame.draw.circle(screen, ring_color, (int(current_x), int(current_y)), int(50 + pulse1), 2)
        pygame.draw.circle(screen, ring_color, (int(current_x), int(current_y)), int(70 + pulse2), 1)

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