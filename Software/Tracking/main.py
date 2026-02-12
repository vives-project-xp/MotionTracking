import pygame
import socket
import sys
import math

# --- CONFIGURATIE ---
UDP_IP = "0.0.0.0" # Luister naar alle binnenkomende data
UDP_PORT = 5005
SMOOTHING = 0.1 # Hoe lager, hoe trager/vloeiender (0.05 - 0.2)

# --- SETUP NETWERK ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

pygame.init()

# Haal de schermresolutie op
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

# Zet het scherm op FULLSCREEN
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Projectie Visuals")
pygame.mouse.set_visible(False)

# Kleuren
ZWART = (0, 0, 0)
NEON_GEEL = (255, 255, 0)
NEON_BLAUW = (0, 255, 255)

# --- FUNCTIE VOOR DE PIJL ---
def draw_dynamic_arrow(surface, color, start, end, thickness=10):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)

    # Als de persoon heel dichtbij het midden is, teken geen pijl
    if dist < 40: return

    # Hoek berekenen
    angle = math.atan2(dy, dx)
    
    # Lijn tekenen
    pygame.draw.line(surface, color, start, end, thickness)
    
    # Pijlpunt berekenen (grootte schaalt mee met afstand)
    head_size = 40 + (dist * 0.02) 
    p1 = (end[0] - head_size * math.cos(angle - 0.5), end[1] - head_size * math.sin(angle - 0.5))
    p2 = (end[0] - head_size * math.cos(angle + 0.5), end[1] - head_size * math.sin(angle + 0.5))
    
    pygame.draw.polygon(surface, color, [end, p1, p2])

# Variabelen voor positie en smoothing
current_x, current_y = WIDTH / 2, HEIGHT / 2
target_x, target_y = WIDTH / 2, HEIGHT / 2

# Main Loop
running = True
while running:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

    # 2. Netwerk Data Ophalen
    try:
        # We lezen alles wat in de buffer zit, pakken de laatste (nieuwste)
        data = None
        while True:
            try:
                chunk, addr = sock.recvfrom(1024)
                data = chunk
            except BlockingIOError:
                break
        
        if data:
            msg = data.decode().split(',')
            rel_x, rel_y = float(msg[0]), float(msg[1])
            
            # Omrekenen van 0-1 naar Scherm Pixels
            target_x = rel_x * WIDTH
            target_y = rel_y * HEIGHT
            
    except (socket.error, ValueError):
        pass 

    # 3. Smoothing (Interpolatie)
    # Dit zorgt ervoor dat de pijl niet stottert, maar glijdt
    current_x += (target_x - current_x) * SMOOTHING
    current_y += (target_y - current_y) * SMOOTHING

    # 4. Tekenen
    screen.fill(ZWART) 
    
    center_screen = (WIDTH // 2, HEIGHT // 2)
    person_pos = (int(current_x), int(current_y))
    
    # Teken de pijl
    draw_dynamic_arrow(screen, NEON_GEEL, center_screen, person_pos)
    
    # Teken een 'target' op de persoon
    pygame.draw.circle(screen, NEON_BLAUW, person_pos, 20, 3) # Open cirkel
    pygame.draw.circle(screen, NEON_GEEL, person_pos, 8)      # Gevulde stip

    # Update scherm
    pygame.display.flip()

pygame.quit()
sys.exit()