#!/bin/bash

# --- OPRUIMEN ---
# Stop alle hangende processen die de Hailo-chip bezet kunnen houden
echo "Bezig met opschonen van oude processen..."
sudo pkill -9 python3 2>/dev/null
sudo pkill -9 gst-launch-1.0 2>/dev/null

# Geef het systeem een fractie van een seconde om de hardware vrij te geven
sleep 0.5

# --- SETUP ---
# Ga naar de hoofdmap van het project
cd "/home/motiontracking/Tracking_Main"

# Activeer de virtuele omgeving
source venv_tracking/bin/activate

# Vertel Python waar de hailo_apps map staat
export PYTHONPATH="$PYTHONPATH:/home/motiontracking/Tracking_Main"

# --- STARTEN ---
echo "Hailo tracker wordt opgestart..."
python3 basic_pipelines/pose_estimation5.py --input /dev/video0
