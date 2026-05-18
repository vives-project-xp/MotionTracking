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
<html lang="nl">
<head>
    <title>Motion Tracking Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>

    <h1>Tracking Control Panel</h1>

    <div class="container">
        
        <div class="card">
            <h3>Effect Modus</h3>
            <div class="mode-grid">
                <button id="mode-MAGIC" class="btn-mode magic {% if state.mode == 'MAGIC' %}active{% endif %}" onclick="update('mode', 'MAGIC')">MAGIC</button>
                <button id="mode-FIRE" class="btn-mode fire {% if state.mode == 'FIRE' %}active{% endif %}" onclick="update('mode', 'FIRE')">FIRE</button>
                <button id="mode-CYBER" class="btn-mode cyber {% if state.mode == 'CYBER' %}active{% endif %}" onclick="update('mode', 'CYBER')">CYBER</button>
                <button id="mode-GHOST" class="btn-mode ghost {% if state.mode == 'GHOST' %}active{% endif %}" onclick="update('mode', 'GHOST')">GHOST</button>
                <button id="mode-COWBOY" class="btn-mode cowboy {% if state.mode == 'COWBOY' %}active{% endif %}" onclick="update('mode', 'COWBOY')">COWBOY</button>
            </div>
        </div>

        <div class="card">
            <h3>Modifiers</h3>
            <div class="slider-group">
                <div class="slider-header">
                    <span class="slider-label">Y-Offset (Hoogte)</span>
                    <span class="slider-val" id="val_offset">{{ state.offset }}</span>
                </div>
                <input type="range" min="-300" max="300" value="{{ state.offset }}" oninput="update('offset', this.value)">
            </div>
            
            <div class="slider-group">
                <div class="slider-header">
                    <span class="slider-label">Particle Spawn Rate</span>
                    <span class="slider-val" id="val_spawn">{{ state.spawn }}</span>
                </div>
                <input type="range" min="0" max="50" value="{{ state.spawn }}" oninput="update('spawn', this.value)">
            </div>
        </div>

        <div class="card">
            <h3>Achtergrond & Media</h3>
            
            <div class="form-group">
                <label class="form-label">Effen kleur</label>
                <input type="color" id="colorPicker" value="#000000" onchange="sendColor(this.value)">
            </div>

            <div class="form-group" style="margin-top: 30px;">
                <label class="form-label">Geselecteerde Media</label>
                {% for file in media_files %}
                    {% set type = 'video' if file.endswith(('.mp4', '.mov', '.avi')) else 'image' %}
                    <div class="media-row">
                        <button class="btn-bg" onclick="updateBg('{{ type }}', '{{ file }}')" title="{{ file }}">
                            <span class="media-badge {% if type == 'video' %}badge-video{% else %}badge-image{% endif %}">
                                {% if type == 'video' %}VID{% else %}IMG{% endif %}
                            </span>
                            {{ file }}
                        </button>
                        <button class="btn-action" onclick="renameFile('{{ file }}')" title="Hernoemen">Wijzig</button>
                        <button class="btn-action delete" onclick="deleteFile('{{ file }}')" title="Verwijderen">Wis</button>
                    </div>
                {% else %}
                    <div style="font-size: 0.875rem; color: var(--text-muted); padding: 10px 0;">Geen media gevonden.</div>
                {% endfor %}
            </div>

            <div class="form-group" style="margin-top: 30px;">
                <label class="form-label">Nieuwe media toevoegen</label>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="text" name="custom_name" placeholder="Optionele bestandsnaam...">
                    <input type="file" name="file" accept="image/*,video/*" required>
                    <button type="submit" class="btn-primary">Uploaden</button>
                </form>
            </div>
        </div>

    </div>

    <script>
        function update(key, val) {
            // Update slider waarden
            if(document.getElementById('val_'+key)) {
                document.getElementById('val_'+key).innerText = val;
            }
            
            // Beheer actieve status voor de mode-knoppen
            if(key === 'mode') {
                // Verwijder de class 'active' van alle knoppen
                document.querySelectorAll('.btn-mode').forEach(btn => btn.classList.remove('active'));
                // Voeg de class 'active' toe aan de specifieke knop waarop net is geklikt
                let activeBtn = document.getElementById('mode-' + val);
                if(activeBtn) activeBtn.classList.add('active');
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
            let baseName = oldName.substring(0, oldName.lastIndexOf('.'));
            let newName = prompt("Voer een nieuwe naam in:", baseName);
            if (newName && newName.trim() !== "") {
                let formData = new FormData();
                formData.append('old_name', oldName);
                formData.append('new_name', newName.trim());
                fetch('/rename', { method: 'POST', body: formData }).then(() => window.location.reload());
            }
        }

        function deleteFile(fileName) {
            if (confirm(`Weet je zeker dat je "${fileName}" wilt verwijderen?`)) {
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