import paho.mqtt.client as mqtt
import json
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import cv2
import hailo

# --- andere files dat later erin komen: ---
from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp

# --- CONFIG ---
MQTT_BROKER = "10.20.10.18"
MQTT_TOPIC = "vj/hailo"
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)

client = mqtt.Client()
try:
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
except:
    print("MQTT Verbinding mislukt")

def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None: return Gst.PadProbeReturn.OK

    format, width, height = get_caps_from_pad(pad)
    frame = get_numpy_from_buffer(buffer, format, width, height)

    marker_data = {}
    if frame is not None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)
        if ids is not None:
            for i, m_id in enumerate(ids.flatten()):
                if m_id < 4:
                    c = corners[i][0]
                    mx = float(np.mean(c[:, 0]) / width)
                    my = float(np.mean(c[:, 1]) / height)
                    marker_data[str(int(m_id))] = [mx, my]

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    people = []

    for d in detections:
        if d.get_label() == "person":
            landmarks = d.get_objects_typed(hailo.HAILO_LANDMARKS)
            if len(landmarks) > 0:
                p = landmarks[0].get_points()
                people.append({
                    "nose": [float(p[0].x()), float(p[0].y())],
                    "left_hand": [float(p[9].x()), float(p[9].y())],
                    "right_hand": [float(p[10].x()), float(p[10].y())]
                })

    payload = {"people": people, "markers": marker_data}
    client.publish(MQTT_TOPIC, json.dumps(payload))
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    app = GStreamerPoseEstimationApp(app_callback, app_callback_class())
    app.video_sink = "fakesink"
    app.use_frame = True
    app.run()