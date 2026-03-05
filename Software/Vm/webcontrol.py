from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Standaard instellingen
state = {
    "mode": "MAGIC",
    "size": 5,
    "offset": 80,
    "spawn": 10
}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Tracking control panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; text-align: center; background: #111; color: white; margin: 0; padding: 20px; }
        .card { background: #222; padding: 20px; border-radius: 15px; display: inline-block; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        button { padding: 15px; margin: 5px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; width: 45%; transition: 0.2s; }
        button:active { transform: scale(0.95); }
        .MAGIC { background: #9b59b6; color: white; } .FIRE { background: #e67e22; color: white; }
        .CYBER { background: #2ecc71; color: white; } .GHOST { background: #bdc3c7; color: black; }
        .slider-container { margin: 25px 0; text-align: left; }
        input[type=range] { width: 100%; height: 10px; border-radius: 5px; background: #444; outline: none; -webkit-appearance: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 22px; height: 22px; background: #2ecc71; border-radius: 50%; cursor: pointer; }
        label { font-size: 0.9em; color: #aaa; text-transform: uppercase; }
        span { float: right; color: #2ecc71; font-weight: bold; }
    </style>
</head>
<body>
    <h1>✨ Tracking control panel</h1>
    <div class="card">
        <h3>Effect Modus</h3>
        <button class="MAGIC" onclick="update('mode', 'MAGIC')">MAGIC</button>
        <button class="FIRE" onclick="update('mode', 'FIRE')">FIRE</button>
        <button class="CYBER" onclick="update('mode', 'CYBER')">CYBER</button>
        <button class="GHOST" onclick="update('mode', 'GHOST')">GHOST</button>

        <div class="slider-container">
            <label>Bol Grootte: <span id="val_size">5</span></label>
            <input type="range" min="1" max="30" value="5" oninput="update('size', this.value)">
        </div>

        <div class="slider-container">
            <label>Hoogte (Offset): <span id="val_offset">80</span></label>
            <input type="range" min="0" max="400" value="80" oninput="update('offset', this.value)">
        </div>

        <div class="slider-container">
            <label>Hoeveelheid: <span id="val_spawn">10</span></label>
            <input type="range" min="1" max="50" value="10" oninput="update('spawn', this.value)">
        </div>
    </div>
    <script>
        function update(key, val) {
            if(key !== 'mode') document.getElementById('val_'+key).innerText = val;
            fetch(`/update?${key}=${val}`, { mode: 'no-cors' });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/update')
def update():
    for key in state:
        val = request.args.get(key)
        if val: state[key] = int(val) if val.isdigit() else val
    return "OK"

@app.route('/get_config')
def get_config(): return jsonify(state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)