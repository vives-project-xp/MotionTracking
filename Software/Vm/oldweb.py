import os
import json
from flask import Flask, render_template_string, request, jsonify, redirect, send_from_directory
from werkzeug.utils import secure_filename
import paho.mqtt.publish as publish

app = Flask(__name__)

# Beveiliging: maximale uploadgrootte instellen (500 MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

MEDIA_FOLDER = 'Media'
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# --- MQTT Configuratie ---
MQTT_BROKER = "127.0.0.1" 
MQTT_TOPIC_CONFIG = "vj/config"

# --- Alleen deze bestandstypes zijn toegestaan ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


state = {
    "mode": "MAGIC",
    "size": 5,
    "offset": 80,
    "spawn": 10,
    "shape": "circle",
    "draw_particles": 1,
    "draw_aura": 1,
    "draw_lines": 0,
    "bg_type": "color",
    "bg_val": "0,0,0",
}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Motion Tracking Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; text-align: center; background: #0a0a0a; color: white; margin: 0; padding: 20px; }
        .card { background: #1a1a1a; padding: 20px; border-radius: 15px; margin: 10px auto; max-width: 450px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); border: 1px solid #333; }
        h3 { border-bottom: 1px solid #444; padding-bottom: 10px; margin-top: 0; color: #ccc; }

        button { padding: 12px; margin: 5px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:active { transform: scale(0.95); }
        
        .btn-mode { width: 22%; font-size: 0.8em; }

        .media-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
        .btn-bg { flex-grow: 1; background: #2980b9; color: white; margin: 0; text-align: left; padding-left: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .btn-rename { width: 45px; background: #f39c12; color: black; margin: 0 0 0 5px; padding: 12px 0; flex-shrink: 0; }
        .btn-delete { width: 45px; background: #e74c3c; color: white; margin: 0 0 0 5px; padding: 12px 0; flex-shrink: 0; }

        .MAGIC { background: #9b59b6; color: white; } 
        .FIRE { background: #e67e22; color: white; }
        .CYBER { background: #2ecc71; color: black; } 
        .GHOST { background: #bdc3c7; color: black; }
        .COWBOY { background: #5d4037; color: white; } /* Bruin voor cowboy */

        input[type=color] { border: none; width: 100%; height: 40px; border-radius: 8px; cursor: pointer; background: none; }
        .upload-form { border: 1px dashed #555; padding: 15px; border-radius: 8px; margin-top: 15px; background: #111; }
        input[type=file] { color: white; margin-bottom: 10px; width: 100%; }
        input[type=text] { width: calc(100% - 20px); padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #555; background: #222; color: white; }
        .btn-upload { background: #2ecc71; color: black; width: 100%; }

        .slider-container { margin: 20px 0; text-align: left; }
        input[type=range] { width: 100%; height: 8px; border-radius: 5px; background: #333; outline: none; -webkit-appearance: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; background: #fff; border-radius: 50%; cursor: pointer; }
        .slider-label { font-size: 0.9em; color: #aaa; text-transform: uppercase; }
        .slider-val { float: right; color: #2ecc71; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🎛️ Tracking Control Panel</h1>

    <div class="card">
        <h3>1. Achtergrond</h3>
        <div style="margin-bottom: 20px;">
            <label style="display:block; text-align:left; color:#aaa; margin-bottom:5px;">Effen kleur:</label>
            <input type="color" id="colorPicker" value="#000000" onchange="sendColor(this.value)">
        </div>

        <div style="text-align: left; margin-bottom: 15px;">
            <label style="color:#aaa; margin-bottom:10px; display:block;">Kies Media:</label>
            {% for file in media_files %}
                {% set type = 'video' if file.endswith(('.mp4', '.mov', '.avi')) else 'image' %}
                <div class="media-row">
                    <button class="btn-bg" onclick="updateBg('{{ type }}', '{{ file }}')" title="{{ file }}">
                        {% if type == 'video' %}🎬{% else %}🖼️{% endif %} {{ file }}
                    </button>
                    <button class="btn-rename" onclick="renameFile('{{ file }}')" title="Hernoemen">✏️</button>
                    <button class="btn-delete" onclick="deleteFile('{{ file }}')" title="Verwijderen">🗑️</button>
                </div>
            {% endfor %}
        </div>

        <div class="upload-form">
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="text" name="custom_name" placeholder="Naam (optioneel)">
                <input type="file" name="file" accept="image/*,video/*" required>
                <button type="submit" class="btn-upload">Uploaden ⬆️</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h3>2. Effect Modus</h3>
        <button class="btn-mode MAGIC" onclick="update('mode', 'MAGIC')">MAGIC</button>
        <button class="btn-mode FIRE" onclick="update('mode', 'FIRE')">FIRE</button>
        <button class="btn-mode CYBER" onclick="update('mode', 'CYBER')">CYBER</button>
        <button class="btn-mode GHOST" onclick="update('mode', 'GHOST')">GHOST</button>
        <button class="btn-mode COWBOY" onclick="update('mode', 'COWBOY')">COWBOY</button>
    </div>

    <div class="card">
        <h3>3. Modifiers</h3>
        <div class="slider-container">
            <span class="slider-label">Y-Offset (Hoogte):</span> <span class="slider-val" id="val_offset">{{ state.offset }}</span>
            <input type="range" min="-300" max="300" value="{{ state.offset }}" oninput="update('offset', this.value)">
        </div>
        <div class="slider-container">
            <span class="slider-label">Particle Spawn Rate:</span> <span class="slider-val" id="val_spawn">{{ state.spawn }}</span>
            <input type="range" min="0" max="50" value="{{ state.spawn }}" oninput="update('spawn', this.value)">
        </div>
    </div>

    <script>
        function update(key, val) {
            if(document.getElementById('val_'+key)) {
                document.getElementById('val_'+key).innerText = val;
            }
            fetch(`/update?${key}=${val}`);
        }

        function updateBg(type, val) {
            fetch(`/update?bg_type=${type}&bg_val=${val}`);
        }

        function sendColor(hex) {
            let r = parseInt(hex.substring(1, 3), 16), g = parseInt(hex.substring(3, 5), 16), b = parseInt(hex.substring(5, 7), 16);
            updateBg('color', `${r},${g},${b}`);
        }

        function renameFile(oldName) {
            let newName = prompt("Nieuwe naam:", oldName.split('.')[0]);
            if (newName) {
                let formData = new FormData();
                formData.append('old_name', oldName);
                formData.append('new_name', newName.trim());
                fetch('/rename', { method: 'POST', body: formData }).then(() => window.location.reload());
            }
        }

        function deleteFile(fileName) {
            if (confirm("Permanent verwijderen?")) {
                let formData = new FormData();
                formData.append('filename', fileName);
                fetch('/delete', { method: 'POST', body: formData }).then(() => window.location.reload());
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    files = []
    if os.path.exists(MEDIA_FOLDER):
        files = [f for f in os.listdir(MEDIA_FOLDER) if allowed_file(f)]
    return render_template_string(HTML, media_files=files, state=state)

@app.route('/update')
def update():
    for key in state:
        val = request.args.get(key)
        if val is not None:
            state[key] = int(val) if val.replace('-', '').isdigit() else val
    try:
        publish.single(MQTT_TOPIC_CONFIG, payload=json.dumps(state), hostname=MQTT_BROKER)
    except Exception as e:
        print(f"MQTT Error: {e}")
    return "OK"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return redirect('/')
    file = request.files['file']
    custom_name = request.form.get('custom_name', '').strip()
    if file.filename == '' or not allowed_file(file.filename): return redirect('/')
    
    ext = os.path.splitext(file.filename)[1].lower()
    filename = (secure_filename(custom_name) + ext) if custom_name else secure_filename(file.filename)
    file.save(os.path.join(MEDIA_FOLDER, filename))
    return redirect('/')

@app.route('/rename', methods=['POST'])
def rename_file():
    old_name, new_name = request.form.get('old_name'), request.form.get('new_name')
    if old_name and new_name:
        old_path = os.path.join(MEDIA_FOLDER, secure_filename(old_name))
        new_path = os.path.join(MEDIA_FOLDER, secure_filename(new_name) + os.path.splitext(old_name)[1])
        if os.path.exists(old_path): os.rename(old_path, new_path)
    return "OK"

@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.form.get('filename')
    if filename:
        filepath = os.path.join(MEDIA_FOLDER, secure_filename(filename))
        if os.path.exists(filepath): os.remove(filepath)
    return "OK"

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, threaded=True)
