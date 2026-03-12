import pygame
import random
import math
import cv2
import os
import numpy as np

# --- 1. EFFECT PRESETS ---
EFFECTS = {
    "MAGIC": {"colors": [(150, 50, 255), (100, 200, 255)], "gravity": 0.0, "decay": (4, 10), "size": (3, 8), "spawn": 8, "trail": 40},
    "FIRE": {"colors": [(255, 60, 0), (255, 150, 0), (255, 230, 50)], "gravity": -0.3, "decay": (8, 15), "size": (4, 10), "spawn": 15, "trail": 60},
    "CYBER": {"colors": [(0, 255, 150), (0, 255, 255)], "gravity": 0.0, "decay": (15, 25), "size": (2, 5), "spawn": 20, "trail": 20},
    "GHOST": {"colors": [(200, 200, 255), (255, 255, 255)], "gravity": 0.02, "decay": (2, 5), "size": (2, 4), "spawn": 4, "trail": 10}
}

# --- 2. BACKGROUND MANAGER (Kleuren, Afbeeldingen & Video) ---
class BackgroundManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.bg_type = 'color'
        self.bg_val = '0,0,0'
        self.cap = None
        self.img_surf = None

    def update_config(self, bg_type, bg_val):
        if self.bg_type == bg_type and self.bg_val == bg_val:
            return # Geen wijziging

        self.bg_type = bg_type
        self.bg_val = bg_val

        # Sluit oude video als we iets anders laden
        if self.cap:
            self.cap.release()
            self.cap = None

        if bg_type == 'image':
            try:
                img = pygame.image.load(os.path.join("Media", bg_val)).convert()
                self.img_surf = pygame.transform.scale(img, (self.width, self.height))
            except Exception as e:
                print(f"Kan afbeelding niet laden: {e}")
                self.bg_type = 'color'; self.bg_val = '0,0,0'
                
        elif bg_type == 'video':
            try:
                self.cap = cv2.VideoCapture(os.path.join("Media", bg_val))
            except Exception as e:
                print(f"Kan video niet laden: {e}")
                self.bg_type = 'color'; self.bg_val = '0,0,0'

    def draw(self, screen):
        if self.bg_type == 'color':
            try:
                c = tuple(map(int, self.bg_val.split(',')))
                screen.fill(c)
            except:
                screen.fill((0,0,0))
                
        elif self.bg_type == 'image' and self.img_surf:
            screen.blit(self.img_surf, (0,0))
            
        elif self.bg_type == 'video' and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                # Video is klaar, start opnieuw (Looping)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            
            if ret:
                # Converteer OpenCV frame naar Pygame Surface
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (self.width, self.height))
                frame = np.swapaxes(frame, 0, 1) # Verwissel X en Y as voor Pygame
                pygame.surfarray.blit_array(screen, frame)


# --- 3. DEELTJES SYSTEEM (Voor de Glow/Neon effecten) ---
class Particle:
    def __init__(self, x, y, cfg, is_hand=False):
        self.x = x; self.y = y
        self.cfg = cfg
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-1.5, 1.5)
        if is_hand: self.vy -= 1.5
            
        self.life = 255
        self.color = random.choice(cfg["colors"])
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
            r = max(1, int(self.size))
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)

# --- 4. LAYER: AURA RINGS ---
def draw_layer_aura(screen, x, y, scale, primary_color, secondary_color, time_val):
    pulse = math.sin(time_val * 5) * 10
    pygame.draw.circle(screen, primary_color, (int(x), int(y)), int((80 * scale) + pulse), max(1, int(3 * scale)))
    pygame.draw.circle(screen, secondary_color, (int(x), int(y)), int((100 * scale) - pulse), max(1, int(1 * scale)))