import pygame
import cv2
import numpy as np
import time
import random
import requests
import paho.mqtt.client as mqtt
import threading
import json
from effects_lib import EFFECTS, Particle, BackgroundManager, draw_layer_aura

# --- CONFIGURATIE ---
VM_IP = "10.20.10.18"
MQTT_TOPIC = "vj/hailo"

data_lock = threading.Lock()
payload = {"people": [], "markers": {}}
calib_done = False
transform_matrix = np.eye(3, dtype=np.float32)
smooth_cache = {}

def on_message(client, userdata, msg):
    global payload
    try:
        data = json.loads(msg.payload.decode())
        with data_lock:
            payload = data
    except: pass

def run_visualizer():
    global payload, calib_done, transform_matrix

    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(VM_IP, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        client.loop_start()
    except: print("Fout: MQTT verbinding mislukt")

    pygame.init()
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h

    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_surfs = [pygame.surfarray.make_surface(cv2.cvtColor(cv2.aruco.generateImageMarker(dict_aruco, i, 200), cv2.COLOR_GRAY2RGB).swapaxes(0, 1)) for i in range(4)]

    cfg = EFFECTS["FIRE"].copy()
    bg_manager = BackgroundManager(W, H, VM_IP)
    particles = []
    effect_surface = pygame.Surface((W, H)).convert()
    effect_surface.set_colorkey((0, 0, 0))
    fade_overlay = pygame.Surface((W, H)).convert()
    fade_overlay.fill((0, 0, 0))

    frame_count = 0

    while True:
        frame_count += 1
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return
                if event.key == pygame.K_c: calib_done = False
                if event.key == pygame.K_s:
                    transform_matrix = np.array([[W, 0, 0], [0, H, 0], [0, 0, 1]], dtype=np.float32)
                    calib_done = True

        if not calib_done:
            screen.fill((255, 255, 255))
            m_size = 150
            margin = 60
            positions = [(margin, margin), (W - m_size - margin, margin), (W - m_size - margin, H - m_size - margin), (margin, H - m_size - margin)]
            half = m_size / 2
            pts_dst = np.array([[p[0] + half, p[1] + half] for p in positions], dtype=np.float32)

            for i, pos in enumerate(positions):
                scaled = pygame.transform.scale(marker_surfs[i], (m_size, m_size))
                screen.blit(scaled, pos)

            with data_lock: markers = payload.get("markers", {})
            if len(markers) >= 4:
                try:
                    src = np.array([markers[str(i)] for i in range(4)], dtype=np.float32)
                    transform_matrix = cv2.getPerspectiveTransform(src, pts_dst)
                    calib_done = True
                except: pass
            pygame.display.flip()
            continue

        if frame_count % 30 == 0:
            try:
                r = requests.get(f"http://{VM_IP}/get_config", timeout=0.1)
                if r.status_code == 200:
                    data = r.json()
                    mode = data.get('mode', 'FIRE')
                    if mode in EFFECTS:
                        cfg = EFFECTS[mode].copy()
                        cfg.update({'spawn': int(data.get('spawn', 10)), 'offset_px': int(data.get('offset', 0))})
                        bg_manager.update_config(data.get('bg_type', 'color'), data.get('bg_val', '0,0,0'))
            except: pass

        bg_manager.draw(screen)
        fade_overlay.set_alpha(cfg.get("trail", 30))
        effect_surface.blit(fade_overlay, (0, 0))

        with data_lock:
            people = list(payload.get("people", []))

        curr_time = time.time()
        for p_idx, person in enumerate(people):
            targets = []
            if "nose" in person: targets.append(("nose", person["nose"]))
            if "left_hand" in person: targets.append(("lh", person["left_hand"]))
            if "right_hand" in person: targets.append(("rh", person["right_hand"]))

            for label, coords in targets:
                try:
                    n_raw = np.array([[[coords[0], coords[1]]]], dtype=np.float32)
                    n_map = cv2.perspectiveTransform(n_raw, transform_matrix)[0][0]

                    tx = n_map[0]

                    ty = n_map[1] + cfg.get('offset_px', 0)

                    tx = np.clip(tx, 0, W)
                    ty = np.clip(ty, 0, H)

                    current_smooth = 0.03 if label == "nose" else 0.20
                    cache_key = f"{p_idx}_{label}"
                    if cache_key not in smooth_cache: smooth_cache[cache_key] = [tx, ty]
                    smooth_cache[cache_key][0] += (tx - smooth_cache[cache_key][0]) * current_smooth
                    smooth_cache[cache_key][1] += (ty - smooth_cache[cache_key][1]) * current_smooth
                    nx, ny = smooth_cache[cache_key]

                    if label == "nose":
                        draw_layer_aura(effect_surface, nx, ny, 1.2, cfg["colors"][0], cfg["colors"][-1], curr_time)

                    for _ in range(cfg.get("spawn", 5)):
                        particles.append(Particle(nx + random.uniform(-10, 10), ny + random.uniform(-10, 10), cfg))
                except: continue

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(effect_surface)

        screen.blit(effect_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    run_visualizer()