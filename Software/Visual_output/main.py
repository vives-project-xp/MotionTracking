import pygame
import cv2
import numpy as np
import time
import random
import paho.mqtt.client as mqtt
import threading
import json
import math
from effects_lib import EFFECTS, Particle, BackgroundManager, draw_layer_aura

# --- CONFIGURATIE ---
VM_IP = "10.20.10.18"
MQTT_TOPIC_DATA = "vj/hailo"
MQTT_TOPIC_CONFIG = "vj/config"

data_lock = threading.Lock()
payload = {"people": [], "markers": {}}
current_config = {"mode": "FIRE", "spawn": 10, "offset": 80, "bg_type": "color", "bg_val": "0,0,0"}
config_updated = True
calib_done = False
transform_matrix = np.eye(3, dtype=np.float32)
smooth_cache = {}

# --- COWBOY FUNCTIES ---
def draw_cowboy_hat(surf, x, y, scale=1.5):
    # Forceer naar integers voor Pygame
    x, y = int(x), int(y)
    w = int(120 * scale)
    h_brim = int(25 * scale)
    h_top = int(45 * scale)
    color = (90, 50, 20)

    # 1. De Rand (Brim)
    brim_rect = (x - w // 2, y - 15, w, h_brim)
    pygame.draw.ellipse(surf, color, brim_rect)
    pygame.draw.ellipse(surf, (0, 0, 0), brim_rect, 2)

    # 2. De Bovenkant (Crown)
    crown_w = int(w * 0.6)
    crown_rect = (x - crown_w // 2, y - 45, crown_w, h_top)
    pygame.draw.ellipse(surf, color, crown_rect)
    pygame.draw.ellipse(surf, (0, 0, 0), crown_rect, 2)

def draw_pitchfork(surf, x, y, scale=2.0):
    # Forceer naar integers voor Pygame
    x, y = int(x), int(y)
    wood_color = (139, 69, 19)
    metal_color = (192, 192, 192)
    black = (0, 0, 0)

    # 1. De Steel
    handle_w = int(16 * scale)
    handle_h = int(140 * scale)
    handle_x = x - (handle_w // 2)
    handle_y = y + int(40 * scale)
    pygame.draw.rect(surf, wood_color, (handle_x, handle_y, handle_w, handle_h))
    pygame.draw.rect(surf, black, (handle_x, handle_y, handle_w, handle_h), 2)

    # 2. De Tanden
    start_y = y + int(40 * scale)
    tine_length = int(60 * scale)
    tine_spacing = int(30 * scale)
    for i in range(-1, 2):
        tx_end = x + (i * tine_spacing)
        ty_end = start_y - tine_length
        pygame.draw.line(surf, metal_color, (x, start_y), (int(tx_end), int(ty_end)), int(6 * scale))
        pygame.draw.line(surf, black, (x, start_y), (int(tx_end), int(ty_end)), 2)

# --- MQTT LOGICA ---
def on_message(client, userdata, msg):
    global payload, current_config, config_updated
    try:
        data = json.loads(msg.payload.decode())
        with data_lock:
            if msg.topic == MQTT_TOPIC_DATA:
                payload = data
            elif msg.topic == MQTT_TOPIC_CONFIG:
                current_config.update(data)
                config_updated = True
    except: pass

def run_visualizer():
    global payload, calib_done, transform_matrix, current_config, config_updated

    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(VM_IP, 1883, 60)
        client.subscribe([(MQTT_TOPIC_DATA, 0), (MQTT_TOPIC_CONFIG, 0)])
        client.loop_start()
    except: print("Fout: MQTT Verbinding")

    pygame.init()
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    bg_manager = BackgroundManager(W, H, VM_IP)
    particles = []
    effect_surface = pygame.Surface((W, H)).convert()
    effect_surface.set_colorkey((0, 0, 0))
    fade_overlay = pygame.Surface((W, H)).convert()
    fade_overlay.fill((0, 0, 0))

    dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_surfs = [pygame.surfarray.make_surface(cv2.cvtColor(cv2.aruco.generateImageMarker(dict_aruco, i, 200), cv2.COLOR_GRAY2RGB).swapaxes(0, 1)) for i in range(4)]

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
            m_size, margin = 150, 60
            positions = [(margin, margin), (W-m_size-margin, margin), (W-m_size-margin, H-m_size-margin), (margin, H-m_size-margin)]
            for i, pos in enumerate(positions):
                screen.blit(pygame.transform.scale(marker_surfs[i], (m_size, m_size)), pos)
            with data_lock: markers = payload.get("markers", {})
            if len(markers) >= 4:
                try:
                    src = np.array([markers[str(i)] for i in range(4)], dtype=np.float32)
                    dst = np.array([[p[0]+m_size/2, p[1]+m_size/2] for p in positions], dtype=np.float32)
                    transform_matrix = cv2.getPerspectiveTransform(src, dst)
                    calib_done = True
                except: pass
            pygame.display.flip()
            continue

        if config_updated:
            with data_lock:
                mode = current_config.get('mode', 'FIRE')
                cfg = EFFECTS.get(mode, EFFECTS["FIRE"]).copy()
                bg_manager.update_config(current_config.get('bg_type', 'color'), current_config.get('bg_val', '0,0,0'))
                config_updated = False

        bg_manager.draw(screen)

        if current_config["mode"] == "COWBOY":
            effect_surface.fill((0, 0, 0)) 
        else:
            fade_overlay.set_alpha(cfg.get("trail", 30))
            effect_surface.blit(fade_overlay, (0, 0))

        with data_lock:
            people = list(payload.get("people", []))

        curr_time = time.time()
        for p_idx, person in enumerate(people):
            parts = [("nose", 0.05), ("left_hand", 0.2), ("right_hand", 0.2)]
            for label, smooth_factor in parts:
                if label in person:
                    raw_coords = np.array([[[person[label][0], person[label][1]]]], dtype=np.float32)
                    mapped = cv2.perspectiveTransform(raw_coords, transform_matrix)[0][0]
                    tx, ty = mapped[0], mapped[1] + current_config.get('offset', 80)

                    key = f"{p_idx}_{label}"
                    if key not in smooth_cache: smooth_cache[key] = [tx, ty]
                    smooth_cache[key][0] += (tx - smooth_cache[key][0]) * smooth_factor
                    smooth_cache[key][1] += (ty - smooth_cache[key][1]) * smooth_factor
                    nx, ny = smooth_cache[key]

                    if current_config["mode"] == "COWBOY":
                        # Gebruik int() bij de aanroep voor extra veiligheid
                        if label == "nose": 
                            draw_cowboy_hat(effect_surface, int(nx), int(ny))
                        if label == "right_hand": 
                            draw_pitchfork(effect_surface, int(nx), int(ny))
                    else:
                        if label == "nose":
                            draw_layer_aura(effect_surface, nx, ny, 1.2, cfg["colors"][0], cfg["colors"][-1], curr_time)
                        for _ in range(current_config.get("spawn", 10)):
                            particles.append(Particle(nx + random.uniform(-10, 10), ny + random.uniform(-10, 10), cfg))

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(effect_surface)

        screen.blit(effect_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    run_visualizer()
