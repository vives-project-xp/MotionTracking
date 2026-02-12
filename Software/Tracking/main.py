import pygame
import socket
import sys

# --- CONFIG ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# --- SETUP NETWERK ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

pygame.init()

# Haal de schermresolutie van je monitor op
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

# Zet het scherm op FULLSCREEN
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Radar Scherm Fullscreen")

# Verberg de muis voor een cleaner effect
pygame.mouse.set_visible(False)

while True:
    screen.fill((30, 30, 30)) 
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # Handig: Druk op 'ESC' om af te sluiten uit fullscreen
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    try:
        data, addr = sock.recvfrom(1024)
        msg = data.decode().split(',')
        rel_x, rel_y = float(msg[0]), float(msg[1])
        
        
        px = int(rel_x * WIDTH)
        py = int(rel_y * HEIGHT)
        
        # Teken het hoofd  
        pygame.draw.rect(screen, (255, 255, 0), (px - 20, py - 20, 40, 40))
        pygame.draw.polygon(screen, (255, 255, 0), [(px, py - 25), (px - 10, py - 45), (px + 10, py - 45)])
        
    except (BlockingIOError, socket.error):
        pass 

    # Teken de rand van het vak (groen)
    pygame.draw.rect(screen, (0, 255, 0), (0, 0, WIDTH, HEIGHT), 10)
    
    pygame.display.flip()