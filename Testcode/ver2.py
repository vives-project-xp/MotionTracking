import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import subprocess
import time

# Start Notepad
subprocess.Popen(["notepad.exe"])
time.sleep(1)  # klein beetje tijd om te openen

# Model laden
base_options = python.BaseOptions(model_asset_path="pose_landmarker_full.task")
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=False,
    running_mode=vision.RunningMode.VIDEO
)
detector = vision.PoseLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

LEFT_WRIST = 15
dragging = False

while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    result = detector.detect_for_video(mp_image, int(time.time() * 1000))

    if result.pose_landmarks:
        lm = result.pose_landmarks[0]

        wrist = lm[LEFT_WRIST]

        # Convert pose coords → screen coords
        screen_w, screen_h = pyautogui.size()
        cursor_x = int(wrist.x * screen_w)
        cursor_y = int(wrist.y * screen_h)

        # Failsafe uit
        pyautogui.FAILSAFE = False

        # Cursor begrenzen
        cursor_x = max(10, min(cursor_x, screen_w - 10))
        cursor_y = max(10, min(cursor_y, screen_h - 10))

        pyautogui.moveTo(cursor_x, cursor_y, duration=0)


        # Detect "drag mode" → arm hoog = slepen
        arm_up = wrist.y < 0.4

        if arm_up and not dragging:
            pyautogui.mouseDown()
            dragging = True

        if not arm_up and dragging:
            pyautogui.mouseUp()
            dragging = False

        # Visual feedback
        cx, cy = int(wrist.x * w), int(wrist.y * h)
        cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)

    cv2.putText(frame, "Arm omhoog = venster slepen", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Arm Control", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
