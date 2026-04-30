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
MQTT_TOPIC_DATA = "vj/hailo"  # Voor pose data
MQTT_TOPIC_CONFIG = "vj/config"  # Voor website config

# State variabelen
data_lock = threading.Lock()
payload = {"people": [], "markers": {}}

# Website configuratie
website_config = {
    "mode": "FIRE",
    "size": 5,
    "offset": "0",
    "spawn": 10,
    "shape": "circle",
    "draw_particles": 1,
    "draw_aura": 1,
    "draw_lines": 0,
    "bg_type": "color",
    "bg_val": "0,0,0",
    "tracker_bron": "camera",
    "target_person": "persoon1"
}
config_lock = threading.Lock()

def on_message_data(client, userdata, msg):
    global payload
    try:
        data = json.loads(msg.payload.decode())
        with data_lock:
            payload = data
    except Exception as e:
        print(f"Fout bij verwerken data bericht: {e}")

def on_message_config(client, userdata, msg):
    global website_config
    try:
        config = json.loads(msg.payload.decode())
        with config_lock:
            website_config.update(config)
            print(f"Nieuwe config ontvangen: {config}")
    except Exception as e:
        print(f"Fout bij verwerken config bericht: {e}")

def on_message_unified(client, userdata, msg):
    """Universele message handler voor zowel data als config"""
    global payload, website_config
    try:
        data = json.loads(msg.payload.decode())

        # Check of het config data is (bevat mode, size, etc.)
        if any(key in data for key in ['mode', 'size', 'offset', 'spawn', 'shape', 'draw_particles']):
            with config_lock:
                website_config.update(data)
                print(f"Config update: {data}")
        else:
            # Het is pose/marker data
            with data_lock:
                payload = data
    except Exception as e:
        print(f"Fout bij verwerken bericht: {e}")

def draw_lines_between_points(surface, points, color, thickness=2):
    """Teken lijnen tussen punten voor connecties"""
    if len(points) < 2:
        return

    for i in range(len(points) - 1):
        start_pos = (int(points[i][0]), int(points[i][1]))
        end_pos = (int(points[i+1][0]), int(points[i+1][1]))
        pygame.draw.line(surface, color, start_pos, end_pos, thickness)

def get_person_by_target(people, target_person):
    """Haal de juiste persoon op basis van target_person"""
    if target_person == "persoon1":
        return people[0] if people else None
    elif target_person == "persoon2":
        return people[1] if len(people) > 1 else None
    # Voorlopig alleen eerste persoon
    return people[0] if people else None

def run_visualizer():
    global payload, website_config

    # MQTT Client opzetten met unified handler
    client = mqtt.Client()
    client.on_message = on_message_unified

    try:
        client.connect(VM_IP, 1883, 60)
        client.subscribe(MQTT_TOPIC_DATA)
        client.subscribe(MQTT_TOPIC_CONFIG)
        client.loop_start()
        print("MQTT verbonden - luistert naar data en config")
    except Exception as e:
        print(f"Fout: MQTT verbinding mislukt: {e}")
        return

    pygame.init()
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h

    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # ArUco markers voor calibratie
    dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_surfs = [pygame.surfarray.make_surface(cv2.cvtColor(cv2.aruco.generateImageMarker(dict_aruco, i, 200), cv2.COLOR_GRAY2RGB).swapaxes(0, 1)) for i in range(4)]

    # Initialiseer managers
    bg_manager = BackgroundManager(W, H, VM_IP)
    particles = []
    effect_surface = pygame.Surface((W, H)).convert()
    effect_surface.set_colorkey((0, 0, 0))
    fade_overlay = pygame.Surface((W, H)).convert()
    fade_overlay.fill((0, 0, 0))

    # Voor lijn tracking
    previous_points = []

    calib_done = False
    transform_matrix = np.eye(3, dtype=np.float32)
    smooth_cache = {}

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

            with data_lock:
                markers = payload.get("markers", {})
            if len(markers) >= 4:
                try:
                    src = np.array([markers[str(i)] for i in range(4)], dtype=np.float32)
                    transform_matrix = cv2.getPerspectiveTransform(src, pts_dst)
                    calib_done = True
                except Exception as e:
                    print(f"Calibratie fout: {e}")
            pygame.display.flip()
            continue

        # --- WEBSITE CONFIG TOE PASSEN ---
        with config_lock:
            current_config = website_config.copy()

        # Effect config opbouwen
        mode = current_config.get('mode', 'FIRE')
        cfg = EFFECTS.get(mode, EFFECTS['FIRE']).copy()

        # Website specifieke instellingen toepassen
        cfg['spawn'] = int(current_config.get('spawn', 10))
        cfg['size'] = (int(current_config.get('size', 5)), int(current_config.get('size', 5)) * 2)
        offset_px = int(current_config.get('offset', '0'))
        shape = current_config.get('shape', 'circle')
        draw_particles = bool(int(current_config.get('draw_particles', 1)))
        draw_aura = bool(int(current_config.get('draw_aura', 1)))
        draw_lines = bool(int(current_config.get('draw_lines', 0)))

        # Achtergrond updaten
        bg_manager.update_config(
            current_config.get('bg_type', 'color'),
            current_config.get('bg_val', '0,0,0')
        )

        # --- ACHTERGROND TEKENEN ---
        bg_manager.draw(screen)

        # Fade effect voor particles
        fade_overlay.set_alpha(cfg.get("trail", 30))
        effect_surface.blit(fade_overlay, (0, 0))

        # --- POSE DATA VERWERKEN ---
        with data_lock:
            people = list(payload.get("people", []))

        # Selecteer target persoon
        target_person = current_config.get('target_person', 'persoon1')
        person = get_person_by_target(people, target_person)

        current_points = []
        curr_time = time.time()

        if person:
            targets = []
            if "nose" in person: targets.append(("nose", person["nose"]))
            if "left_hand" in person: targets.append(("lh", person["left_hand"]))
            if "right_hand" in person: targets.append(("rh", person["right_hand"]))

            for label, coords in targets:
                try:
                    n_raw = np.array([[[coords[0], coords[1]]]], dtype=np.float32)
                    n_map = cv2.perspectiveTransform(n_raw, transform_matrix)[0][0]

                    tx = n_map[0]
                    ty = n_map[1] + offset_px

                    tx = np.clip(tx, 0, W)
                    ty = np.clip(ty, 0, H)

                    # Smoothing
                    current_smooth = 0.03 if label == "nose" else 0.20
                    cache_key = f"{label}"
                    if cache_key not in smooth_cache:
                        smooth_cache[cache_key] = [tx, ty]
                    smooth_cache[cache_key][0] += (tx - smooth_cache[cache_key][0]) * current_smooth
                    smooth_cache[cache_key][1] += (ty - smooth_cache[cache_key][1]) * current_smooth
                    nx, ny = smooth_cache[cache_key]

                    current_points.append((nx, ny))

                    # Aura tekenen als ingeschakeld
                    if draw_aura and label == "nose":
                        draw_layer_aura(effect_surface, nx, ny, 1.2, cfg["colors"][0], cfg["colors"][-1], curr_time)

                    # Particles spawnen als ingeschakeld
                    if draw_particles:
                        for _ in range(cfg.get("spawn", 5)):
                            particles.append(Particle(nx + random.uniform(-10, 10), ny + random.uniform(-10, 10), cfg, is_hand=(label in ["lh", "rh"])))

                except Exception as e:
                    print(f"Fout bij verwerken {label}: {e}")
                    continue

        # Lijnen tekenen tussen punten als ingeschakeld
        if draw_lines and len(current_points) >= 2:
            draw_lines_between_points(effect_surface, current_points, cfg["colors"][0], 3)
            previous_points = current_points.copy()

        # Particles updaten en tekenen
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(effect_surface)

        # Effect surface blitten
        screen.blit(effect_surface, (0, 0), special_flags=pygame.BLEND_ADD)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    run_visualizer()