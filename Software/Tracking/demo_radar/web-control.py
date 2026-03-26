import os
from flask import Flask, render_template_string, request, jsonify, redirect, send_from_directory

app = Flask(__name__)

# Maak de Media map aan op de server als deze niet bestaat
MEDIA_FOLDER = 'Media'
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# Standaard instellingen
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
    "tracker_bron": "camera"  # Standaard op camera
}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>VJ Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; text-align: center; background: #0a0a0a; color: white; margin: 0; padding: 20px; }
        .card { background: #1a1a1a; padding: 20px; border-radius: 15px; margin: 10px auto; max-width: 450px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); border: 1px solid #333; }
        h3 { border-bottom: 1px solid #444; padding-bottom: 10px; margin-top: 0; color: #ccc; }

        button { padding: 12px; margin: 5px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:active { transform: scale(0.95); }

        .btn-tracker { width: 45%; background: #444; color: white; border: 2px solid #222; }
        .btn-mode { width: 22%; font-size: 0.8em; }
        .btn-bg { width: 45%; background: #2980b9; color: white; margin-bottom: 10px; }
        .btn-shape { width: 30%; background: #555; color: white; }

        .MAGIC { background: #9b59b6; color: white; } .FIRE { background: #e67e22; color: white; }
        .CYBER { background: #2ecc71; color: black; } .GHOST { background: #bdc3c7; color: black; }

        input[type=color] { border: none; width: 100%; height: 40px; border-radius: 8px; cursor: pointer; background: none; }
        .upload-form { border: 1px dashed #555; padding: 15px; border-radius: 8px; margin-top: 15px; background: #111; }
        input[type=file] { color: white; margin-bottom: 10px; width: 100%; }
        .btn-upload { background: #2ecc71; color: black; width: 100%; }

        .toggle-group { text-align: left; margin: 15px 0; }
        .toggle-label { font-size: 1.1em; cursor: pointer; display: block; margin: 10px 0; background: #222; padding: 10px; border-radius: 8px; border-left: 4px solid #2ecc71; }
        input[type=checkbox] { transform: scale(1.5); margin-right: 15px; accent-color: #2ecc71; }

        .slider-container { margin: 20px 0; text-align: left; }
        input[type=range] { width: 100%; height: 8px; border-radius: 5px; background: #333; outline: none; -webkit-appearance: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; background: #fff; border-radius: 50%; cursor: pointer; }
        .slider-label { font-size: 0.9em; color: #aaa; text-transform: uppercase; }
        .slider-val { float: right; color: #2ecc71; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🎛️ VJ Dashboard</h1>

    <div class="card">
        <h3>🎯 Tracking Bron</h3>
        <button class="btn-tracker" id="btn_camera" onclick="update('tracker_bron', 'camera'); highlightTracker('camera')">📷 Camera (AI)</button>
        <button class="btn-tracker" id="btn_radar" onclick="update('tracker_bron', 'radar'); highlightTracker('radar')">📡 Radar (ESP32)</button>
    </div>

    <div class="card">
        <h3>1. Achtergrond</h3>

        <div style="margin-bottom: 20px;">
            <label style="display:block; text-align:left; color:#aaa; margin-bottom:5px;">Kies een effen kleur:</label>
            <input type="color" id="colorPicker" value="#000000" onchange="sendColor(this.value)">
        </div>

        <div style="text-align: left; margin-bottom: 15px;">
            <label style="color:#aaa;">Kies Media (Gedownload naar Pi):</label><br>
            {% for file in media_files %}
                {% set type = 'video' if file.endswith(('.mp4', '.mov', '.avi')) else 'image' %}
                <button class="btn-bg" onclick="updateBg('{{ type }}', '{{ file }}')">
                    {% if type == 'video' %}🎬{% else %}🖼️{% endif %} {{ file }}
                </button>
            {% endfor %}
            {% if not media_files %}
                <p style="color:#777; font-size: 0.9em;">Geen media gevonden. Upload iets hieronder!</p>
            {% endif %}
        </div>

        <div class="upload-form">
            <form action="/upload" method="post" enctype="multipart/form-data">
                <label style="display:block; text-align:left; color:#aaa; margin-bottom:5px;">Upload nieuwe media:</label>
                <input type="file" name="file" accept="image/*,video/*" required>
                <button type="submit" class="btn-upload">Bestand Uploaden ⬆️</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h3>2. Effect Kleuren</h3>
        <button class="btn-mode MAGIC" onclick="update('mode', 'MAGIC')">MAGIC</button>
        <button class="btn-mode FIRE" onclick="update('mode', 'FIRE')">FIRE</button>
        <button class="btn-mode CYBER" onclick="update('mode', 'CYBER')">CYBER</button>
        <button class="btn-mode GHOST" onclick="update('mode', 'GHOST')">GHOST</button>
    </div>

    <div class="card">
        <h3>3. Foreground Layers</h3>
        <div class="toggle-group">
            <label class="toggle-label"><input type="checkbox" checked onchange="update('draw_particles', this.checked ? 1 : 0)"> ✨ Particles Layer</label>
            <label class="toggle-label"><input type="checkbox" checked onchange="update('draw_aura', this.checked ? 1 : 0)"> ⭕ Aura Rings Layer</label>
        </div>

        <div style="margin-top: 15px;">
            <button class="btn-shape" onclick="update('shape', 'circle')">⚫ Circle</button>
            <button class="btn-shape" onclick="update('shape', 'square')">⬛ Square</button>
            <button class="btn-shape" onclick="update('shape', 'triangle')">▲ Triangle</button>
        </div>
    </div>

    <div class="card">
        <h3>4. Modifiers</h3>
        <div class="slider-container">
            <span class="slider-label">Master Size:</span> <span class="slider-val" id="val_size">5</span>
            <input type="range" min="1" max="30" value="5" oninput="update('size', this.value)">
        </div>
        <div class="slider-container">
            <span class="slider-label">Y-Offset (Hoogte):</span> <span class="slider-val" id="val_offset">80</span>
            <input type="range" min="-100" max="300" value="80" oninput="update('offset', this.value)">
        </div>
        <div class="slider-container">
            <span class="slider-label">Particle Spawn Rate:</span> <span class="slider-val" id="val_spawn">10</span>
            <input type="range" min="0" max="50" value="10" oninput="update('spawn', this.value)">
        </div>
    </div>

    <script>
        function update(key, val) {
            if(document.getElementById('val_'+key)) {
                document.getElementById('val_'+key).innerText = val;
            }
            fetch(`/update?${key}=${val}`, { mode: 'no-cors' });
        }

        function updateBg(type, val) {
            fetch(`/update?bg_type=${type}&bg_val=${val}`, { mode: 'no-cors' });
        }

        function sendColor(hex) {
            let r = parseInt(hex.substring(1, 3), 16);
            let g = parseInt(hex.substring(3, 5), 16);
            let b = parseInt(hex.substring(5, 7), 16);
            updateBg('color', `${r},${g},${b}`);
        }

        // Visuele feedback voor de tracker knoppen
        function highlightTracker(bron) {
            document.getElementById('btn_camera').style.border = (bron === 'camera') ? '2px solid #2ecc71' : '2px solid transparent';
            document.getElementById('btn_radar').style.border = (bron === 'radar') ? '2px solid #2ecc71' : '2px solid transparent';
        }

        // Zet de highlight goed bij het laden van de pagina
        window.onload = function() {
            highlightTracker('camera');
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    # Lees alle bestanden in de Media map om de knoppen te genereren
    files = []
    if os.path.exists(MEDIA_FOLDER):
        files = [f for f in os.listdir(MEDIA_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov', '.avi'))]
    return render_template_string(HTML, media_files=files)

@app.route('/update')
def update():
    for key in state:
        val = request.args.get(key)
        if val is not None:
            state[key] = int(val) if val.isdigit() else val
    return "OK"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return redirect('/')
    file = request.files['file']
    if file.filename != '':
        # Sla het bestand op in de Media map van de VM/PC
        file.save(os.path.join(MEDIA_FOLDER, file.filename))
    # Herlaad de pagina, de nieuwe knop staat er nu bij!
    return redirect('/')

# --- DEZE ROUTE IS CRUCIAAL ---
# Hiermee kan de Raspberry Pi het geüploade bestand downloaden via HTTP
@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/get_config')
def get_config():
    return jsonify(state)

if __name__ == '__main__':
    # Start de server op poort 80
    app.run(host='0.0.0.0', port=80, threaded=True)