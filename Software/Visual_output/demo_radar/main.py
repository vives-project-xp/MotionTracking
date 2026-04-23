import pygame
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import math
import multiprocessing
import random
import requests
import paho.mqtt.client as mqtt
from ultralytics import YOLO

# --- IMPORTEER JE EIGEN BIBLIOTHEEK ---
from effects_lib import EFFECTS, Particle, BackgroundManager, draw_layer_aura

# --- 1. CONFIGURATIE ---
VM_IP = "10.20.10.18"  # IP van de VM met webcontrol.py en de MQTT Broker
ACTIVE_MODE = "FIRE"
CAMERA_INDEX = 0
CAMERA_RES = (640, 480)
ARUCO_DICT = aruco.DICT_4X4_50
REQUIRED_STABLE_TIME = 1.0

ZWART = (0, 0, 0)
WIT = (255, 255, 255)
ROOD = (255, 0, 0)

# --- GLOBALE VARIABELE VOOR RADAR ---
radar_data = {"detected": False, "angle": 0.0, "distance": 0.0}

def on_mqtt_connect(client, userdata, flags, rc):
    print(f"[MQTT] Verbonden met code {rc}. Luisteren naar radar...")
    client.subscribe("vj/radar")

def on_mqtt_message(client, userdata, msg):
    global radar_data
    try:
        payload = msg.payload.decode('utf-8')
        hoek, afstand = map(float, payload.split(','))
        # Afstand is in mm. Als afstand groter is dan 0, is er iemand
        if afstand > 0:
            radar_data = {"detected": True, "angle": hoek, "distance": afstand}
        else:
            radar_data["detected"] = False
    except:
        pass


# --- 2. TRACKER (YOLO Pose + ArUco) ---
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
            results = model(frame, verbose=False, imgsz=160, stream=True)
            all_people_data = []

            for r in results:
                if r.keypoints and len(r.keypoints.xy) > 0:
                    for person_kpts in r.keypoints.xy.cpu().numpy():
                        if len(person_kpts) > 10:
                            nose, l_hand, r_hand = person_kpts[0], person_kpts[9], person_kpts[10]

                            if cv2.pointPolygonTest(fixed_pts.astype(np.int32), (float(nose[0]), float(nose[1])), False) >= 0:
                                tp = cv2.perspectiveTransform(np.array([[[nose[0], nose[1]]]], dtype=np.float32), transform_matrix)[0][0]
                                person_dict = {"body": (float(tp[0]), float(tp[1])), "hands": []}

                                for hand in [l_hand, r_hand]:
                                    if hand[0] > 0:
                                        tp_h = cv2.perspectiveTransform(np.array([[[hand[0], hand[1]]]], dtype=np.float32), transform_matrix)[0][0]
                                        person_dict["hands"].append((float(tp_h[0]), float(tp_h[1])))

                                all_people_data.append(person_dict)

            if all_people_data and not shared_queue.full():
                shared_queue.put(all_people_data, block=False)
    cap.release()


# --- 3. VISUALIZER ---
def run_visualizer(shared_queue, stop_event, is_calibrated_flag):
    # Start MQTT Client voor de Radar
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    try:
        mqtt_client.connect(VM_IP, 1883, 60)
        mqtt_client.loop_start() # Draait op de achtergrond
    except Exception as e:
        print(f"[Waarschuwing] Kon niet verbinden met MQTT Broker op {VM_IP}: {e}")

    # Start Pygame
    pygame.init()
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    marker_imgs = []
    for i in range(4):
        try: marker_imgs.append(pygame.transform.scale(pygame.image.load(f"Markers/marker{i}.png"), (200, 200)))
        except: s = pygame.Surface((200, 200)); s.fill(ROOD); marker_imgs.append(s)

    cfg = EFFECTS[ACTIVE_MODE].copy()
    cfg.update({
        'offset_px': 80, 'spawn': 10, 'current_size_val': 5, 
        'draw_particles': 1, 'draw_aura': 1,
        'bg_type': 'color', 'bg_val': '0,0,0',
        'tracker_bron': 'camera'
    })

    people_list = []
    particles = []
    
    bg_manager = BackgroundManager(WIDTH, HEIGHT, VM_IP)
    
    effect_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
    effect_surface.fill(ZWART)
    fade_overlay = pygame.Surface((WIDTH, HEIGHT)).convert()
    fade_overlay.fill(ZWART)

    frame_count = 0

    while not stop_event.is_set():
        frame_count += 1
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: stop_event.set()

        # KALIBRATIE SCHERM (Voor Camera)
        if is_calibrated_flag.value == 0:
            screen.fill(WIT)
            for i, pos in enumerate([(50, 50), (WIDTH-250, 50), (50, HEIGHT-250), (WIDTH-250, HEIGHT-250)]):
                screen.blit(marker_imgs[i], pos)
            pygame.display.flip()
            continue

        # API CALL: Web Paneel uitlezen
        if frame_count % 30 == 0:
            try:
                r = requests.get(f"http://{VM_IP}/get_config", timeout=0.05)
                if r.status_code == 200:
                    data = r.json()
                    cfg = EFFECTS[data['mode']].copy()
                    cfg.update({
                        'current_size_val': int(data.get('size', 5)),
                        'spawn': int(data.get('spawn', 10)),
                        'offset_px': int(data.get('offset', 80)),
                        'draw_particles': int(data.get('draw_particles', 1)),
                        'draw_aura': int(data.get('draw_aura', 1)),
                        'bg_type': data.get('bg_type', 'color'),
                        'bg_val': data.get('bg_val', '0,0,0'),
                        'tracker_bron': data.get('tracker_bron', 'camera')
                    })
                    cfg['size'] = (cfg['current_size_val'], cfg['current_size_val']+4)
                    bg_manager.update_config(cfg['bg_type'], cfg['bg_val'])
            except: pass

        # --- TRACKING BRON SELECTEREN ---
        tracker_bron = cfg.get('tracker_bron', 'camera')
        people_list = []

        if tracker_bron == 'camera':
            # Haal YOLO data op
            try:
                while not shared_queue.empty(): 
                    people_list = shared_queue.get_nowait()
            except: pass
            
        elif tracker_bron == 'radar':
            # Haal de live geüpdatete radar_data op (Afstand in Millimeters!)
            if radar_data["detected"]:
                # SCHAALFACTOR: Hoeveel pixels is 1 millimeter in de echte wereld?
                # Pas dit aan om het perfect af te stemmen op de grootte van je projectie!
                PIXELS_PER_MM = 0.5 
                
                # Goniometrie: Hoek (graden) naar radialen
                rad_angle = math.radians(radar_data["angle"])
                
                # --- OMDRAAIEN X en Y ---
                # X: '-' in plaats van '+' (draait links en rechts om)
                radar_x = (WIDTH / 2) - (math.sin(rad_angle) * radar_data["distance"] * PIXELS_PER_MM)
                
                # Y: Geen 'HEIGHT -' meer. Dichterbij de radar (0) is nu bovenaan het scherm (Y=0)
                radar_y = (math.cos(rad_angle) * radar_data["distance"] * PIXELS_PER_MM)
                
                # Zorg dat de persoon binnen het scherm blijft (0.0 tot 1.0 genormaliseerd)
                norm_x = max(0.0, min(1.0, radar_x / WIDTH))
                norm_y = max(0.0, min(1.0, radar_y / HEIGHT))
                
                # Vorm het om naar hetzelfde format als de camera
                people_list = [{"body": (norm_x, norm_y), "hands": []}]

        # --- TEKENEN IN LAGEN ---
        
        # 1. Achtergrond (Media/Kleur)
        bg_manager.draw(screen)

        # 2. Vervaag oude effecten (Trails)
        fade_overlay.set_alpha(cfg["trail"])
        effect_surface.blit(fade_overlay, (0,0))

        scale = cfg['current_size_val'] / 5.0
        current_time = time.time()

        # 3. Nieuwe effecten genereren per persoon
        for person in people_list:
            bx, by = person["body"][0]*WIDTH, person["body"][1]*HEIGHT
            v_y = by - cfg['offset_px']
            color_primary = cfg["colors"][0]
            color_secondary = cfg["colors"][-1]
            scaled_hands = [(h[0]*WIDTH, h[1]*HEIGHT) for h in person["hands"]]

            if cfg['draw_aura'] == 1:
                draw_layer_aura(effect_surface, bx, v_y, scale, color_primary, color_secondary, current_time)

            if cfg['draw_particles'] == 1:
                for _ in range(cfg["spawn"]):
                    ang, r = random.uniform(0, 6.28), random.uniform(30, 70) * scale
                    particles.append(Particle(bx + math.cos(ang)*r, v_y + math.sin(ang)*r, cfg))
                for h in scaled_hands:
                    for _ in range(int(cfg["spawn"] / 3) + 1):
                        particles.append(Particle(h[0], h[1], cfg, is_hand=True))

        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            elif cfg['draw_particles'] == 1:
                p.draw(effect_surface)

        # 4. COMPOSITING: Effecten blenden (Add-modus voor neon-look)
        screen.blit(effect_surface, (0,0), special_flags=pygame.BLEND_ADD)

        pygame.display.flip()
        clock.tick(60)
        
    mqtt_client.loop_stop()
    pygame.quit()

if __name__ == "__main__":
    q = multiprocessing.Queue(maxsize=2)
    stop, calib = multiprocessing.Event(), multiprocessing.Value('i', 0)
    p = multiprocessing.Process(target=run_tracker, args=(q, stop, calib))
    p.start()
    try: run_visualizer(q, stop, calib)
    finally:
        stop.set()
        p.join()