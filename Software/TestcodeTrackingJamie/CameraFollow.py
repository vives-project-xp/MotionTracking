import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
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

NOSE = 0

# Zoom factor (hoe kleiner, hoe meer zoom)
ZOOM = 0.4   # 40% van het beeld wordt gebruikt

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
        nose = lm[NOSE]

        # Hoofdpositie in pixels
        cx = int(nose.x * w)
        cy = int(nose.y * h)

        # Bepaal crop-grootte
        crop_w = int(w * ZOOM)
        crop_h = int(h * ZOOM)

        # Centreer crop rond hoofd
        x1 = cx - crop_w // 2
        y1 = cy - crop_h // 2
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        # Grenzen corrigeren
        x1 = max(0, min(x1, w - crop_w))
        y1 = max(0, min(y1, h - crop_h))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        # Crop en zoom
        cropped = frame[y1:y2, x1:x2]
        zoomed = cv2.resize(cropped, (w, h))

        cv2.putText(zoomed, "Head Tracking Active", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Head Tracking Camera", zoomed)

    else:
        cv2.imshow("Head Tracking Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
