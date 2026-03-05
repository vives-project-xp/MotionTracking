import cv2

# Initialiseer de camera (0 is meestal de standaard webcam)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Kan de camera niet openen.")
    exit()

print("Camera geopend. Druk op 'q' om af te sluiten.")

while True:
    # Frame-voor-frame vastleggen
    ret, frame = cap.read()

    if not ret:
        print("Kan geen beelden ontvangen. Controleer de verbinding.")
        break

    # Toon het resultaat in een venster genaamd 'Webcam'
    cv2.imshow('Webcam', frame)

    # Wacht op de 'q' toets om de loop te breken
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Alles netjes opruimen als we klaar zijn
cap.release()
cv2.destroyAllWindows()