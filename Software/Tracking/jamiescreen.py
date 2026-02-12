import cv2
import cv2.aruco as aruco
import numpy as np
import time
from ultralytics import YOLO
import socket
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURATIE ---
# LET OP: Gebruik "127.0.0.1" als alles op 1 pc draait.
# Gebruik het IP van de andere laptop als je via netwerk stuurt.
TARGET_IP = "10.10.1.70"
UDP_PORT = 5005

# --- SETUP ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
model = YOLO('yolov8n.pt') 

print("Camera wordt opgestart...")
# Let op: cv2.CAP_DSHOW is voor Windows. Gebruik cv2.CAP_V4L2 op Raspberry Pi.
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

fixed_pts = None
transform_matrix = None # We slaan de matrix hier op
start_lock_time = None
is_locked = False
required_stable_time = 2 # Iets korter gemaakt voor sneller testen

# --- MediaPipe Pose Landmarker (full body) ---
base_options = python.BaseOptions(model_asset_path="pose_landmarker_full.task")
pose_options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=False,
    running_mode=vision.RunningMode.VIDEO
)
pose_detector = vision.PoseLandmarker.create_from_options(pose_options)

# Pose connections for drawing skeleton
POSE_CONNECTIONS = [
    (11, 13), (13, 15),  # Left arm
    (12, 14), (14, 16),  # Right arm
    (11, 12),            # Shoulders
    (23, 24),            # Hips
    (11, 23), (12, 24),  # Torso
    (23, 25), (25, 27),  # Left leg
    (24, 26), (26, 28),  # Right leg
    (27, 29), (29, 31),  # Left foot
    (28, 30), (30, 32),  # Right foot
]

print("Wachten op ArUco markers (0, 1, 2, 3)...")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    # Pose detection + drawing (zichtbaar tijdens kalibratie en tracking)
    h, w, _ = frame.shape
    try:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        pose_result = pose_detector.detect_for_video(mp_image, int(time.time() * 1000))

        if pose_result.pose_landmarks:
            lm = pose_result.pose_landmarks[0]

            # Draw landmarks
            for i, landmark in enumerate(lm):
                cx = int(landmark.x * w)
                cy = int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

            # Draw skeleton connections
            for a, b in POSE_CONNECTIONS:
                ax = int(lm[a].x * w)
                ay = int(lm[a].y * h)
                bx = int(lm[b].x * w)
                by = int(lm[b].y * h)
                cv2.line(frame, (ax, ay), (bx, by), (0, 255, 255), 2)
    except Exception:
        # If MediaPipe isn't available or errors, silently continue (keeps previous behavior)
        pass
    if not is_locked:
        # --- FASE 1: KALIBREREN ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        
        points = {}
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            for i in range(len(ids)):
                points[ids[i][0]] = corners[i][0]
            
            # Check of alle 4 hoeken er zijn (linksboven, rechtsboven, linksonder, rechtsonder)
            if all(id in points for id in [0, 1, 2, 3]):
                if start_lock_time is None: start_lock_time = time.time()
                elapsed = time.time() - start_lock_time
                
                # Volgorde: 0=TL, 1=TR, 3=BR, 2=BL
                tl, tr, br, bl = points[0][0], points[1][1], points[3][2], points[2][3]
                temp_pts = np.array([tl, tr, br, bl], np.int32).reshape((-1, 1, 2))
                
                # Teken geel kader tijdens locken
                cv2.polylines(frame, [temp_pts], True, (0, 255, 255), 2)
                cv2.putText(frame, f"Locking: {int(elapsed)}/{required_stable_time}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                if elapsed >= required_stable_time:
                    fixed_pts = temp_pts
                    
                    # --- OPTIMALISATIE: Matrix EENMALIG berekenen ---
                    src_pts = fixed_pts.reshape(4, 2).astype(np.float32)
                    dst_pts = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=np.float32)
                    transform_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    
                    is_locked = True
                    print("Vak vergrendeld! Start nu main.py")
            else:
                start_lock_time = None # Reset timer als een marker wegvalt
    else:
        # --- FASE 2: TRACKING ---
        # Teken het vastgezette kader (groen)
        cv2.polylines(frame, [fixed_pts], True, (0, 255, 0), 2)
        
        # YOLO detectie (alleen personen = class 0)
        results = model(frame, verbose=False, classes=[0], stream=True) 

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # We pakken niet het midden van de hele box, maar iets hoger (hoofd/borst)
                # Dit voorkomt dat de pijl naar je kruis wijst
                center_x = int((x1 + x2) / 2)
                center_y = int(y1 + (y2 - y1) * 0.3) 
                anchor_point = (center_x, center_y)

                # Check of persoon BINNEN het geprojecteerde kader staat
                is_inside = cv2.pointPolygonTest(fixed_pts, (float(center_x), float(center_y)), False)

                if is_inside >= 0:
                    # Gebruik de vooraf berekende matrix
                    p = np.array([[[center_x, center_y]]], dtype=np.float32)
                    tp = cv2.perspectiveTransform(p, transform_matrix)[0][0]
                    
                    # Verstuur data: "x,y" (tussen 0.0 en 1.0)
                    msg = f"{tp[0]:.3f},{tp[1]:.3f}"
                    sock.sendto(msg.encode(), (TARGET_IP, UDP_PORT))

                    # Visual feedback op camera
                    cv2.circle(frame, anchor_point, 5, (0, 0, 255), -1)
                    cv2.putText(frame, "TRACKING", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('Tracker Debug', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('r'): # Reset
        is_locked = False
        start_lock_time = None
        fixed_pts = None

cap.release()
cv2.destroyAllWindows()