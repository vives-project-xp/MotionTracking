import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera kan niet geopend worden")
    exit()

while True:
    ok, frame = cap.read()
    if not ok:
        print("Geen frame ontvangen")
        break

    cv2.imshow("Test Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
