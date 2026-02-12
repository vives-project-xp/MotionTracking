import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import subprocess
import math

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

# Geschiedenis van punten voor tekenen
points = []
MAX_TIME = 2.0  # seconden voordat de lijn verdwijnt

last_clear = time.time()

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

        # Polspositie in pixels
        px = int(wrist.x * w)
        py = int(wrist.y * h)

        # Punt opslaan met timestamp
        points.append((px, py, time.time()))

        # Oude punten verwijderen
        points = [p for p in points if time.time() - p[2] < MAX_TIME]

        # Lijn tekenen
        for i in range(1, len(points)):
            x1, y1, _ = points[i - 1]
            x2, y2, _ = points[i]
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)

        # Pols markeren
        cv2.circle(frame, (px, py), 10, (0, 255, 0), -1)

    cv2.putText(frame, "Handpad wordt getekend (verdwijnt na 2s)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Hand Drawing", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
