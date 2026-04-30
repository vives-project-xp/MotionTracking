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
    except:
        pass


def draw_cowboy_hat(surf, x, y, scale=1.0):
    """Teken cowboy-hoed boven het hoofd"""
    hat_width = int(120 * scale)
    hat_height = int(30 * scale)
    brim_height = int(15 * scale)
    top_height = int(40 * scale)

    hat_color = (90, 50, 20)
    band_color = (180, 100, 40)

    brim_rect = pygame.Rect(int(x - hat_width / 2), int(y - top_height - brim_height), hat_width, brim_height)
    pygame.draw.ellipse(surf, hat_color, brim_rect)
    pygame.draw.ellipse(surf, (0, 0, 0), brim_rect, 2)

    top_rect = pygame.Rect(int(x - hat_width * 0.35), int(y - top_height - brim_height - top_height), int(hat_width * 0.7), top_height)
    pygame.draw.ellipse(surf, hat_color, top_rect)
    pygame.draw.ellipse(surf, (0, 0, 0), top_rect, 2)

    band_rect = pygame.Rect(int(x - hat_width * 0.25), int(y - top_height - brim_height - top_height / 2), int(hat_width * 0.5), int(hat_height * 0.5))
    pygame.draw.rect(surf, band_color, band_rect)
    pygame.draw.rect(surf, (0, 0, 0), band_rect, 2)


def draw_cowboy_face(surf, x, y, scale=1.0):
    """Teken alleen cowboy-hoed (geen gezicht)"""
    draw_cowboy_hat(surf, x, y - int(60 * scale), scale)


def draw_cowboy_glove(surf, x, y, size=15):
    """Teken cowboy-handschoen/hand"""
    glove_color = (170, 120, 80)
    pygame.draw.circle(surf, glove_color, (int(x), int(y)), size)
    pygame.draw.circle(surf, (0, 0, 0), (int(x), int(y)), size, 2)
    finger_offset = size * 0.6
    angles = [45, 135, 225, 315]
    for angle in angles:
        rad = math.radians(angle)
        fx = x + math.cos(rad) * finger_offset
        fy = y + math.sin(rad) * finger_offset
        pygame.draw.circle(surf, glove_color, (int(fx), int(fy)), int(size * 0.4))
        pygame.draw.circle(surf, (0, 0, 0), (int(fx), int(fy)), int(size * 0.4), 1)


def draw_pitchfork(surf, x, y, scale=1.0):
    """Teken grote hooivork"""
    fork_length = int(150 * scale)  # Steel kleiner gemaakt van 200 naar 150
    fork_width = int(40 * scale)
    tine_length = int(60 * scale)  # Kleiner gemaakt van 80 naar 60
    tine_spacing = int(30 * scale)

    wood_color = (139, 69, 19)
    metal_color = (192, 192, 192)

    # Hoger plaatsen door y_offset van 50 naar 100
    y_offset = int(100 * scale)
    pygame.draw.rect(surf, wood_color, (int(x - fork_width / 2), int(y + y_offset), fork_width, fork_length))
    pygame.draw.rect(surf, (0, 0, 0), (int(x - fork_width / 2), int(y + y_offset), fork_width, fork_length), 2)

    for i in range(3):
        tine_x = x - tine_spacing + i * tine_spacing
        pygame.draw.line(surf, metal_color, (int(tine_x), int(y + y_offset)), (int(tine_x), int(y + y_offset - tine_length)), 8)
        pygame.draw.line(surf, (0, 0, 0), (int(tine_x), int(y + y_offset)), (int(tine_x), int(y + y_offset - tine_length)), 2)


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
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_c:
                    calib_done = False
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

            with data_lock:
                markers = payload.get("markers", {})
            if len(markers) >= 4:
                try:
                    src = np.array([markers[str(i)] for i in range(4)], dtype=np.float32)
                    transform_matrix = cv2.getPerspectiveTransform(src, pts_dst)
                    calib_done = True
                except:
                    pass
            pygame.display.flip()
            continue

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

        bg_manager.draw(screen)
        fade_overlay.set_alpha(cfg.get("trail", 30))
        effect_surface.blit(fade_overlay, (0, 0))

        with data_lock:
            people = list(payload.get("people", []))

        for p_idx, person in enumerate(people):
            try:
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

                    draw_cowboy_face(effect_surface, fx, fy, scale=1.5)

                for hand_type in ["left_hand", "right_hand"]:
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

                        if hand_type == "right_hand":
                            draw_pitchfork(effect_surface, hx, hy, scale=2.4)
                        else:
                            draw_cowboy_glove(effect_surface, hx, hy, size=20)
                            for _ in range(max(1, cfg.get("spawn", 10) // 4)):
                                particles.append(Particle(hx + random.uniform(-15, 15), hy + random.uniform(-15, 15), cfg))
            except:
                continue

        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(effect_surface)

        screen.blit(effect_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    run_visualizer()
