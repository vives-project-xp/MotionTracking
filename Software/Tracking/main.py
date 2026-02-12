import pygame
import socket
import sys
import math

# --- CONFIG ---
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

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
pygame.display.set_caption("Radar Scherm Fullscreen")
pygame.mouse.set_visible(False)

# --- FUNCTIE VOOR DE PIJL ---
def draw_arrow(surface, color, start, end, width=5, head_size=30):
    # Bereken afstand tussen midden en persoon
    if math.dist(start, end) < 20: 
        return 
    
    # Teken de lijn (de steel van de pijl)
    pygame.draw.line(surface, color, start, end, width)
    
    # Bereken de hoek van de pijl
    rotation = math.atan2(start[1] - end[1], end[0] - start[0]) + math.pi/2
    
    # Teken de punt (driehoek)
    pygame.draw.polygon(surface, color, (
        (end[0] + head_size * math.sin(rotation), end[1] + head_size * math.cos(rotation)),
        (end[0] + head_size * math.sin(rotation - 2.3), end[1] + head_size * math.cos(rotation - 2.3)),
        (end[0] + head_size * math.sin(rotation + 2.3), end[1] + head_size * math.cos(rotation + 2.3)),
    ))

# Variabelen om de positie te onthouden (voor als er even geen UDP pakket is)
px, py = WIDTH // 2, HEIGHT // 2

while True:
    screen.fill((30, 30, 30)) 
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    # Probeer nieuwe data te ontvangen
    try:
        data, addr = sock.recvfrom(1024)
        msg = data.decode().split(',')
        rel_x, rel_y = float(msg[0]), float(msg[1])
        
        # Bereken de pixels op basis van schermresolutie
        px = int(rel_x * WIDTH)
        py = int(rel_y * HEIGHT)
        
    except (BlockingIOError, socket.error):
        # Geen nieuwe data, we gebruiken de oude px, py
        pass 

    # --- TEKENWERK ---
    center_screen = (WIDTH // 2, HEIGHT // 2)
    
    # Teken de pijl van het midden naar de persoon
    # Kleur: Geel (255, 255, 0), zoals in je originele code
    draw_arrow(screen, (255, 255, 0), center_screen, (px, py), width=8, head_size=40)
    
    # Teken een cirkel om de persoon (optioneel, voor de duidelijkheid)
    pygame.draw.circle(screen, (255, 255, 0), (px, py), 15, 2)

    # Teken de groene rand van het scherm
    pygame.draw.rect(screen, (0, 255, 0), (0, 0, WIDTH, HEIGHT), 10)
    
    pygame.display.flip()