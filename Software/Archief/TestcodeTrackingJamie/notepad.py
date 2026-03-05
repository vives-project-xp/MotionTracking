import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import subprocess
import time

# Model laden
base_options = python.BaseOptions(model_asset_path="pose_landmarker_full.task")
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=False,
    running_mode=vision.RunningMode.VIDEO
)
detector = vision.PoseLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

last_trigger = 0
cooldown = 2

# Landmark indexen
LEFT_SHOULDER = 11
LEFT_WRIST = 15

while True:
    ok, frame = cap.read()
    if not ok:
        break

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    result = detector.detect_for_video(mp_image, int(time.time() * 1000))

    if result.pose_landmarks:
        lm = result.pose_landmarks[0]

        h, w, _ = frame.shape

        # Landmarks tekenen
        for landmark in lm:
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        # Linkerarm detectie
        shoulder = lm[LEFT_SHOULDER]
        wrist = lm[LEFT_WRIST]

        left_arm_up = wrist.y < shoulder.y - 0.05

        if left_arm_up and time.time() - last_trigger > cooldown:
            subprocess.Popen(["notepad.exe"])
            last_trigger = time.time()

    cv2.putText(frame, "Linkerhand omhoog = Notepad openen", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Movement Detector", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
