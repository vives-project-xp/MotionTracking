import pygame
import cv2
import numpy as np
import time
import random
import paho.mqtt.client as mqtt
import threading
import json
import math
from effects_lib import EFFECTS, Particle, BackgroundManager

# --- CONFIGURATIE ---
VM_IP = "10.20.10.18"
MQTT_TOPIC = "vj/hailo"
MQTT_TOPIC_CONFIG = "vj/config"

# State variabelen
data_lock = threading.Lock()
payload = {"people": [], "markers": {}}

# Voor de configuratie
current_config = {
    "mode": "FIRE",
    "spawn": 10,
    "offset": 80,
    "bg_type": "color",
    "bg_val": "0,0,0"
}
config_updated = False

calib_done = False
transform_matrix = np.eye(3, dtype=np.float32)
smooth_cache = {}

def on_message(client, userdata, msg):
    global payload, current_config, config_updated
    try:
        data = json.loads(msg.payload.decode())
        with data_lock:
            payload = data
    except: pass

def draw_pig_ears(surf, x, y, scale=1.0):
    """Teken Varkentje's oren"""
    ear_color = (255, 150, 150)  # Lichtroos
    ear_size = int(25 * scale)
    ear_offset = int(35 * scale)
    # Linkeroortje
    pygame.draw.circle(surf, ear_color, (int(x - ear_offset), int(y - ear_offset)), ear_size)
    pygame.draw.circle(surf, (200, 100, 100), (int(x - ear_offset), int(y - ear_offset)), ear_size, 2)
    # Rechteroortje
    pygame.draw.circle(surf, ear_color, (int(x + ear_offset), int(y - ear_offset)), ear_size)
    pygame.draw.circle(surf, (200, 100, 100), (int(x + ear_offset), int(y - ear_offset)), ear_size, 2)

def draw_pig_face(surf, x, y, scale=1.0):
    """Teken Varkentje's gezicht"""
    # Roze gezicht
    face_radius = int(50 * scale)
    pygame.draw.circle(surf, (255, 180, 180), (int(x), int(y)), face_radius)
    pygame.draw.circle(surf, (200, 100, 100), (int(x), int(y)), face_radius, 3)
    
    # Oren
    draw_pig_ears(surf, x, y, scale)
    
    # Zwarte ogen
    eye_y = int(y - 15 * scale)
    eye_size = int(8 * scale)
    pygame.draw.circle(surf, (0, 0, 0), (int(x - 15 * scale), eye_y), eye_size)
    pygame.draw.circle(surf, (0, 0, 0), (int(x + 15 * scale), eye_y), eye_size)
    # Witte pupillen
    pygame.draw.circle(surf, (255, 255, 255), (int(x - 15 * scale), eye_y), int(eye_size * 0.4))
    pygame.draw.circle(surf, (255, 255, 255), (int(x + 15 * scale), eye_y), int(eye_size * 0.4))
    
    # Snuit (ronde neus)
    snout_radius = int(20 * scale)
    pygame.draw.circle(surf, (255, 200, 200), (int(x), int(y + 10 * scale)), snout_radius)
    pygame.draw.circle(surf, (200, 100, 100), (int(x), int(y + 10 * scale)), snout_radius, 2)
    # Neusgaten
    pygame.draw.circle(surf, (0, 0, 0), (int(x - 5 * scale), int(y + 10 * scale)), int(3 * scale))
    pygame.draw.circle(surf, (0, 0, 0), (int(x + 5 * scale), int(y + 10 * scale)), int(3 * scale))

def draw_pig_hoof(surf, x, y, size=15):
    """Teken Varkentje's hoef/poot"""
    # Roze poot
    hoof_color = (255, 180, 180)
    pygame.draw.circle(surf, hoof_color, (int(x), int(y)), size)
    pygame.draw.circle(surf, (200, 100, 100), (int(x), int(y)), size, 2)
    # Hoeven (4 kleine bolletjes)
    hoof_offset = size * 0.6
    angles = [45, 135, 225, 315]
    for angle in angles:
        rad = math.radians(angle)
        fx = x + math.cos(rad) * hoof_offset
        fy = y + math.sin(rad) * hoof_offset
        pygame.draw.circle(surf, (200, 150, 150), (int(fx), int(fy)), int(size * 0.3))
        pygame.draw.circle(surf, (150, 80, 80), (int(fx), int(fy)), int(size * 0.3), 1)

def run_visualizer():
    global payload, calib_done, transform_matrix, current_config, config_updated

    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(VM_IP, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        client.loop_start()
    except: 
        print("Fout: MQTT verbinding mislukt")

    pygame.init()
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h

    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_surfs = [pygame.surfarray.make_surface(cv2.cvtColor(cv2.aruco.generateImageMarker(dict_aruco, i, 200), cv2.COLOR_GRAY2RGB).swapaxes(0, 1)) for i in range(4)]

    # Initialiseer de manager
    cfg = EFFECTS["FIRE"].copy()
    bg_manager = BackgroundManager(W, H, VM_IP)
    particles = []
    effect_surface = pygame.Surface((W, H)).convert()
    effect_surface.set_colorkey((0, 0, 0))
    fade_overlay = pygame.Surface((W, H)).convert()
    fade_overlay.fill((0, 0, 0))

    while True:
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

        # --- MQTT CONFIG CHECK ---
        if config_updated:
            with data_lock:
                mode = current_config.get('mode', 'FIRE')
                if mode in EFFECTS:
                    cfg = EFFECTS[mode].copy()
                    cfg.update({
                        'spawn': int(current_config.get('spawn', 10)), 
                        'offset_px': int(current_config.get('offset', 0))
                    })
                    bg_manager.update_config(current_config.get('bg_type', 'color'), current_config.get('bg_val', '0,0,0'))
                config_updated = False
        # --------------------------------------------------------

        bg_manager.draw(screen)
        fade_overlay.set_alpha(cfg.get("trail", 30))
        effect_surface.blit(fade_overlay, (0, 0))

        with data_lock:
            people = list(payload.get("people", []))

        curr_time = time.time()
        for p_idx, person in enumerate(people):
            try:
                # NEUS = Mickey's gezicht
                if "nose" in person:
                    coords = person["nose"]
                    n_raw = np.array([[[coords[0], coords[1]]]], dtype=np.float32)
                    n_map = cv2.perspectiveTransform(n_raw, transform_matrix)[0][0]
                    nx = np.clip(n_map[0], 0, W)
                    ny = np.clip(n_map[1] + cfg.get('offset_px', 0), 0, H)
                    
                    cache_key = f"{p_idx}_nose"
                    if cache_key not in smooth_cache: 
                        smooth_cache[cache_key] = [nx, ny]
                    smooth_cache[cache_key][0] += (nx - smooth_cache[cache_key][0]) * 0.03
                    smooth_cache[cache_key][1] += (ny - smooth_cache[cache_key][1]) * 0.03
                    fx, fy = smooth_cache[cache_key]
                    
                    # Teken Varkentje gezicht
                    draw_pig_face(effect_surface, fx, fy, scale=1.5)

                # HANDEN = Mickey's handschoenen
                for hand_type, hand_idx in [("left_hand", 9), ("right_hand", 10)]:
                    if hand_type in person:
                        coords = person[hand_type]
                        h_raw = np.array([[[coords[0], coords[1]]]], dtype=np.float32)
                        h_map = cv2.perspectiveTransform(h_raw, transform_matrix)[0][0]
                        hx = np.clip(h_map[0], 0, W)
                        hy = np.clip(h_map[1] + cfg.get('offset_px', 0), 0, H)
                        
                        cache_key = f"{p_idx}_{hand_type}"
                        if cache_key not in smooth_cache: 
                            smooth_cache[cache_key] = [hx, hy]
                        smooth_cache[cache_key][0] += (hx - smooth_cache[cache_key][0]) * 0.20
                        smooth_cache[cache_key][1] += (hy - smooth_cache[cache_key][1]) * 0.20
                        hx, hy = smooth_cache[cache_key]
                        
                        # Teken Joker handschoen (geen vuur effect)
                        draw_joker_glove(effect_surface, hx, hy, size=20)

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
