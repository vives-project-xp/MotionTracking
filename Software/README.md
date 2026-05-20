# Software
> Hier vindt men alle software

## Bestandsstructuur

```text
Software/
└── Archief
    └── Oude mappen/bestanden
└── Arduino
    └── Files voor Arduino
└── Hailo_tracking
    └── basic_pipelines
    └── hailo_apps
└── Radar/
    └── Radar_Code/
        └── Radar_Code.ino
└── Visual_output
    └── demo_radar: files om radar te tonen op projector
    └── Markers: fiducials om projector uit te lezen
    └── Media: Foto's en video's voor op projector
    └── files om programma uit te voeren voor op de rock       
└── Vm
    └── files voor de website

    
```
---
## VM - Web control panel

De map `Vm` bevat de webinterface waarmee de visuals op afstand worden ingesteld. Deze software draait op de virtuele machine/server en stuurt configuratie door via MQTT naar het toestel dat de projectie uitvoert.

### Inhoud van de map

| Bestand/map | Functie |
|-------------|---------|
| `webcontrol.py` | Hoofdversie van het Flask webpaneel. Dit script draait op poort `80`, laadt de styling uit `static/style.css` en publiceert instellingen naar MQTT. |
| `oldweb.py` | Oude versie van het webpaneel, bewaard als backup. |
| `static/style.css` | CSS-bestand voor de opmaak van de webinterface. Flask serveert dit bestand automatisch via de `static` map. |
| `Media/` | Wordt automatisch aangemaakt. Hierin komen geuploade afbeeldingen en videos terecht. |

### Werking

De VM draait een Flask-server. Via de website kan men:

- een achtergrondkleur kiezen;
- een afbeelding of video uploaden als achtergrond;
- media hernoemen of verwijderen;
- een effectmodus kiezen, zoals `MAGIC`, `FIRE`, `CYBER`, `GHOST` of `COWBOY`;
- parameters aanpassen zoals `offset` en `spawn`;
- de trackingbron en doelpersoon instellen.

Bij elke wijziging stuurt `webcontrol.py` de volledige configuratie als JSON naar het MQTT-topic:

```text
vj/config
```

De MQTT broker staat standaard ingesteld op:

```python
MQTT_BROKER = "127.0.0.1"
```

Dit betekent dat de MQTT broker op dezelfde VM moet draaien als het webpaneel.

De HTML van het controlepaneel staat nog in `webcontrol.py`, maar de visuele opmaak staat apart in `static/style.css`. Hierdoor kan de layout aangepast worden zonder de Flask-routes of MQTT-logica te wijzigen.

### Installatie op de VM

Installeer Python en de nodige packages:

```bash
pip install flask werkzeug paho-mqtt
```

Zorg ook dat er een MQTT broker draait, bijvoorbeeld Mosquitto:

```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Starten

Navigeer naar de map:

```bash
cd Software/Vm
```

Start daarna het webpaneel:

```bash
python3 webcontrol.py
```

De website is bereikbaar via:

```text
http://<VM-IP>:80
```

Let op: poort `80` vereist op Linux vaak administratorrechten. Gebruik in dat geval:

```bash
sudo python3 webcontrol.py
```

### Belangrijke endpoints

| Endpoint | Functie |
|----------|---------|
| `/` | Hoofdpagina van het controlepaneel. |
| `/update` | Past instellingen aan en publiceert deze via MQTT. |
| `/upload` | Uploadt afbeeldingen of videos naar de VM. |
| `/rename` | Hernoemt een mediabestand. |
| `/delete` | Verwijdert een mediabestand. |
| `/media/<filename>` | Maakt media beschikbaar voor de visual-output client. |
| `/get_config` | Geeft de huidige configuratie terug als JSON. |

---
## Visual_output - Projectie en effecten

De map `Visual_output` bevat de software die op het projectietoestel draait, bijvoorbeeld een Radxa Rock 5B. Deze software opent een fullscreen Pygame-venster op de projector en tekent effecten op basis van trackingdata en instellingen uit de VM.

### Inhoud van de map

| Bestand/map | Functie |
|-------------|---------|
| `main.py` | Hoofdprogramma voor de live visual-output. |
| `effects_lib.py` | Bevat de effect-presets, particle-logica, aura-effecten en background manager. |
| `requirements.txt` | Python dependencies voor de visual-output software. |
| `Media/` | Lokale cache voor afbeeldingen en videos die als achtergrond gebruikt worden. |
| `Markers/` | ArUco/fiducial markers voor projectorkalibratie. |
| `demo_radar/` | Demo-opstelling voor radarvisualisatie. |
| `Back_up*.py`, `old-main.py`, `main3.py`, `main_website.py` | Oudere of experimentele versies van de visual-output. |
| `yolov8n.pt` | YOLO modelbestand voor detectie/testopstellingen. |

### Werking

`main.py` luistert via MQTT naar twee topics:

| Topic | Inhoud |
|-------|--------|
| `vj/hailo` | Trackingdata van personen en markers. |
| `vj/config` | Instellingen vanuit het VM-webpaneel. |

De trackingdata bevat onder andere personen, lichaamsposities en markerposities. De configuratie bepaalt de achtergrond, kleurmodus, particle-spawn en offset.

De belangrijkste stappen in het programma zijn:

1. Verbinden met de MQTT broker op de VM.
2. Fullscreen Pygame-venster openen op de projector.
3. Kalibratiemarkers tonen zolang het scherm nog niet gekalibreerd is.
4. Een perspectieftransformatie berekenen zodra de markers herkend worden.
5. Trackingpunten omzetten naar projectorcoordinaten.
6. Achtergrond tekenen.
7. Effecten, aura's en particles tekenen rond handen en hoofd.

### Configuratie

In `main.py` moet het IP-adres van de VM juist staan:

```python
VM_IP = "10.20.10.18"
```

Pas dit aan naar het IP-adres van de VM waarop `webcontrol.py` en de MQTT broker draaien.

### Installatie

Navigeer naar de map:

```bash
cd Software/Visual_output
```

Maak eventueel een virtuele omgeving aan:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installeer daarna de dependencies:

```bash
pip install -r requirements.txt
```

De gebruikte packages zijn onder andere:

- `pygame`
- `opencv-python`
- `numpy`
- `requests`
- `paho-mqtt`

### Starten

Start de visual-output:

```bash
python3 main.py
```

Het programma opent in fullscreen. Gebruik deze toetsen tijdens het draaien:

| Toets | Functie |
|-------|---------|
| `ESC` | Programma afsluiten. |
| `C` | Kalibratie opnieuw uitvoeren. |
| `S` | Kalibratie overslaan en het volledige scherm gebruiken. |

### Achtergronden en media

Wanneer via de VM een afbeelding of video gekozen wordt, controleert `BackgroundManager` of het bestand lokaal bestaat in `Visual_output/Media`. Als het bestand ontbreekt, wordt het automatisch gedownload vanaf:

```text
http://<VM-IP>/media/<filename>
```

Zo hoeft media enkel via het webpaneel op de VM geupload te worden. De visual-output haalt de bestanden zelf op wanneer ze nodig zijn.

### Kalibratie

Bij het opstarten toont `main.py` vier markers op de hoeken van het projectiebeeld. De camera/trackingsoftware moet deze markers detecteren en via `vj/hailo` doorsturen. Zodra alle vier markers gekend zijn, berekent de visual-output een perspectieftransformatie zodat de trackingpunten correct op de projectie verschijnen.

Als de markers niet gebruikt worden of als er snel getest moet worden, kan met `S` een standaardmapping over het volledige scherm gebruikt worden.

---
## Ai-Thinker RD-03D Radar Software

### Hoe de software werkt

#### 1. Data Ontvangst
De sensor stuurt pakketjes van **30 bytes** via UART op **256000 baud**. De software controleert eerst de volledige header én footer om te bevestigen dat het om een geldig datapakket gaat:

| Positie | Waarde | Beschrijving |
|---------|--------|--------------|
| Byte 0  | `0xAA` | Header byte 1 |
| Byte 1  | `0xFF` | Header byte 2 |
| Byte 2  | `0x03` | Header byte 3 |
| Byte 3  | `0x00` | Header byte 4 |
| Byte 4-5 | variabel | X-coördinaat (little-endian) |
| Byte 6-7 | variabel | Y-coördinaat (little-endian) |
| Byte 8-9 | variabel | Snelheid |
| Byte 10-11 | variabel | Afstandsresolutie |
| Byte 12-27 | `0x00` | Target 2 & 3 (niet gebruikt) |
| Byte 28 | `0x55` | Footer byte 1 |
| Byte 29 | `0xCC` | Footer byte 2 |

De software valideert elk frame door de header (`0xAA 0xFF 0x03 0x00`) en footer (`0x55 0xCC`) te controleren. Frames die hier niet aan voldoen worden weggegooid.

---

#### 2. Coördinaat Decodering
De ruwe X- en Y-waardes worden samengesteld via little-endian optelling:
**X-coördinaat (links/rechts):**
De sensor gebruikt een gedeeld bereik rond 32768 (2¹⁵):
- Rechterkant (positief): `x_raw < 32768` → `x_mm = x_raw`
- Linkerkant (negatief): `x_raw >= 32768` → `x_mm = -(x_raw - 32768)`

**Y-coördinaat (afstand voorwaarts):**
$$y_{mm} = y_{raw} - 32768$$

---

#### 3. Wiskundige Berekening
De software rekent de X- en Y-coördinaten om naar poolcoördinaten:

**Afstand** via de stelling van Pythagoras:
$$\text{afstand} = \frac{\sqrt{x_{mm}^2 + y_{mm}^2}}{10} \text{ cm}$$

**Hoek** via atan2:
$$\text{hoek} = \arctan2(x_{mm},\ y_{mm}) \times \frac{180}{\pi} \text{ graden}$$

Waarbij $0°$ recht vooruit is voor de radar, positieve graden rechts en negatieve graden links.

---

#### 4. Filters
Om ongeldige frames te verwijderen:
1. **Frame lengte**: Exact 30 bytes.
2. **Header & footer**: Moeten exact overeenkomen.
3. **Y-waarde**: Moet groter zijn dan 0 (target moet voor de sensor staan).

---

#### 5. MQTT Verzending
Na een geldige meting wordt de data via WiFi gepubliceerd op het MQTT topic `vj/radar` als CSV-string:

---


#### Gebruik in de Arduino IDE

1. Stel jouw **WiFi credentials** in bovenaan de code.
2. Stel het correcte **MQTT broker IP-adres** in (`mqtt_server`).
3. Upload de code naar de ESP32.
4. Open de **Serial Monitor** (`Ctrl` + `Shift` + `L`) op **115200 baud**.
5. De ESP32 verbindt automatisch met WiFi en de MQTT broker.
6. Je ziet nu serial output zoals: *X,Y,Distance,Angle*

### Bij de Arduino Uno
Om de data te ontvangen van de MQTT broker bij de Arduino Uno (die wordt gebruikt om de motoren aan te sturen) gebruiken we een tweede ESP32 omdat deze wel met Wifi kan verbinden.
We subcriben op de top vj/radar.
Zo sturen we dan alle data die we binnenkrijgen van de topic over de TX-pin die verbonden is met pin 2 op de Arduino.

### Documentatie Arduino
De documentaie over de arduino kan men [hier](/Documentatie/README.md) vinden.

---

**Richting referentie:**
- Beweeg je naar **links**? → Hoek gaat naar **negatieve** graden.
- Beweeg je naar **rechts**? → Hoek gaat naar **positieve** graden.
- Recht voor de sensor = **0°**.

---

### Gebruikte Libraries

| Library | Functie | Installatie |
|---------|---------|-------------|
| `WiFi.h` | WiFi verbinding | Ingebouwd in ESP32 core |
| `PubSubClient.h` | MQTT communicatie | Via Arduino Library Manager |
| `Arduino.h` | Arduino basis | Ingebouwd |

--- 
### Gebruikte Driver
[Driver](https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip)

# Werking van de Hailo AI

Voor dit project hebben we de officiële **Hailo voorbeelden** (examples) van GitHub gehaald. Omdat die code standaard alleen bedoeld is om dingen op een scherm te laten zien, hebben we de code zelf aangepast. Hierdoor kunnen we nu specifiek de houding (pose estimation) van mensen uitlezen en deze data doorsturen.

---

## 🚀 Hoe werkt de Hailo software in dit project?

De code van GitHub zorgt ervoor dat de camera en de Hailo AI-chip (de NPU) met elkaar praten. Dit gebeurt via een zogenaamde video-pipeline. 

Wij hebben ingegrepen op het moment dat er een video-beeld binnenkomt. De Hailo-software doet dan achter de schermen het zware werk:

1. **Scannen naar mensen:** De AI scant het beeld en zoekt naar objecten met het label `"person"`.
2. **Kader maken (Bounding Box):** Als de AI een persoon vindt, trekt hij er een onzichtbaar kader omheen. De software onthoudt de coördinaten van dit kader (waar begint en stopt de persoon in het beeld).
3. **Skeletpunten zoeken (Landmarks):** Binnen dat kader gaat de AI op zoek naar het 'skelet' van de persoon. 

---

## 🛠️ Wat hebben wij aangepast voor de Pose Estimation?

De standaard code van GitHub gooit alle data op één grote hoop. Wij hebben de code zo aangepast dat we heel specifiek drie belangrijke punten uit het skelet filteren:
* De **neus**
* De **linkerhand**
* De **rechterhand**

### De berekening simpel uitgelegd
De Hailo geeft de locatie van de hand of neus door *binnen het kader van de persoon zelf*, en dus niet binnen het hele videoscherm. 

Wij hebben code toegevoegd die dit omrekent. Onze aanpassing zorgt ervoor dat de software kijkt naar de grootte van het kader, berekent waar de hand zich bevindt op het totale scherm, en dit omzet naar een simpel getal tussen `0.0` (helemaal links/boven) en `1.0` (helemaal rechts/onder).

Hierdoor hebben we een super nauwkeurige meting van waar de neus en handen zijn, die we direct kunnen doorsturen via MQTT!
