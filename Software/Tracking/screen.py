import cv2
import cv2.aruco as aruco
import numpy as np
import time
from ultralytics import YOLO
import socket

# --- NETWERK SETUP ---
UDP_IP = "10.10.1.70" 
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

model = YOLO('yolov8n.pt') 

print("Camera wordt opgestart...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()

fixed_pts = None
start_lock_time = None
is_locked = False
required_stable_time = 3 

while True:
    ret, frame = cap.read()
    if not ret: break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    if not is_locked:
        corners, ids, rejected = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        points = {}
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)
            for i in range(len(ids)):
                points[ids[i][0]] = corners[i][0]
            if all(id in points for id in [0, 1, 2, 3]):
                if start_lock_time is None: start_lock_time = time.time()
                elapsed = time.time() - start_lock_time
                tl, tr, br, bl = points[0][0], points[1][1], points[3][2], points[2][3]
                temp_pts = np.array([tl, tr, br, bl], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [temp_pts], True, (0, 255, 255), 2)
                if elapsed >= required_stable_time:
                    fixed_pts = temp_pts
                    is_locked = True
                    print("Vak vergrendeld! Start nu mainscreen.py")
            else:
                start_lock_time = None
    else:
        cv2.polylines(frame, [fixed_pts], True, (0, 255, 0), 2)
        results = model(frame, verbose=False, classes=[0]) 

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                hoofd_hoogte = int((y2 - y1) * 0.30)
                hx1, hy1 = x1, y1
                hx2, hy2 = x2, y1 + hoofd_hoogte
                anchor_point = (int((hx1 + hx2) / 2), int((hy1 + hy2) / 2))
                
                is_inside = cv2.pointPolygonTest(fixed_pts, (float(anchor_point[0]), float(anchor_point[1])), False)

                if is_inside >= 0:
                    
                    src_pts = fixed_pts.reshape(4, 2).astype(np.float32)
                    dst_pts = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=np.float32)
                    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    p = np.array([[[anchor_point[0], anchor_point[1]]]], dtype=np.float32)
                    tp = cv2.perspectiveTransform(p, M)[0][0]
                    
                    
                    sock.sendto(f"{tp[0]},{tp[1]}".encode(), (UDP_IP, UDP_PORT))

                    cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (255, 255, 0), 2)
                    cv2.putText(frame, "In vak", (hx1, hy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    cv2.imshow('Detection Camera', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('r'):
        is_locked = False
        start_lock_time = None

cap.release()
cv2.destroyAllWindows()