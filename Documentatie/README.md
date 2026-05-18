# Documentatie
> Hier vindt men alle documentatie

# Pan and Tilt Joint
Voor dit project hebben wij een pan and tilt joint gebruikt dat alle richtingen in kan draaien. Hiervoor bestaat all een mooi bestaand project: https://www.thingiverse.com/thing:4316563
We kunnen hier vinden hoedat wij het samen stellen: https://www.youtube.com/watch?v=uJO7mv4-0PY
Voor het grote rollement hebben wij dit ook uitgeprint en met gesmeerd zodat het vlot draait.
Beide Stepper Motors namelijk de NEMA-17 Zijn verbonden met QShield v5d en het shield is verbonden aan de Arduino. Het QShield heeft min 12V nodig We voeden het met een adapter van 12V en 2A, Dit is genoeg voor onze stepper motors. Daarna hebben wij deze lamp gemonteerd op het statief: https://www.bax-shop.be/nl/pinspot/eurolite-led-pst-12w-6000k-spot-smalle-beam-pinspot, Dit moet niet deze lamp zijn, maar is onze prefernce.

# Code Pan and Tilt Joint
De code werd geschreven in C in Arduino IDE voor de Arduino Uno dat wij in dit project gebruiken. Je kunt de Code hier vinden: https://github.com/vives-project-xp/MotionTracking/tree/main/Software/Arduino Wat deze code doet is homen van de Y-axis zodat wij niet over de fysieke limiten gaan en het inlezen van de waardes van de mqtt dat vanuit de radar komt.


# Radar Code Documentatie

## Overzicht
Deze code leest de data van een **Ai-Thinker RD-03D** mmWave radar sensor via UART, verwerkt de ruwe frames naar bruikbare coördinaten en stuurt deze via **MQTT over WiFi** door naar de rest van het systeem.

---

## Benodigde Libraries

| Library | Functie | Installatie |
|---------|---------|-------------|
| `WiFi.h` | WiFi verbinding | Ingebouwd in ESP32 core |
| `PubSubClient.h` | MQTT communicatie | Via Arduino Library Manager |
| `secrets.h` | WiFi & MQTT credentials | Zelf aanmaken (zie hieronder) |

---
## Gebruikte Artikels

[**Klik Hier**](https://www.electroniclinic.com/rd-03d-mmwave-radar-multi-human-tracking-with-distance-speed-positioning/)

## Configuratie

### secrets.h
Maak een bestand `secrets.h` aan in dezelfde map als de `.ino` file met de volgende inhoud:

```cpp
#ifndef SECRETS_H
#define SECRETS_H

#define SECRET_SSID "JOUW_WIFI_NAAM"
#define SECRET_PASS "JOUW_WIFI_PASWOORD"
#define SECRET_MQTT_SERVER "JOUW_IP_MQTT_SERVER"

#endif
```

### Pin configuratie
| Definitie | Pin | Beschrijving |
|-----------|-----|--------------|
| `RX_PIN` | 19 | UART ontvangst van radar TX |
| `TX_PIN` | 18 | UART verzending naar radar RX |
| `BAUD_RATE` | 256000 | UART snelheid |

---

## Hoe de code werkt

### 1. Opstarten (`setup`)
- Start de seriële monitor op 115200 baud voor debug output
- Start UART communicatie met de radar op 256000 baud
- Stuurt het `Single_Target_Detection_CMD` commando naar de radar om single-target modus te activeren
- Verbindt met WiFi via `setup_wifi()`
- Verbindt met de MQTT broker

### 2. Hoofdlus (`loop`)
- Controleert of de MQTT verbinding nog actief is, anders herverbindt via `reconnect()`
- Leest continu bytes binnen van de radar via UART
- Wanneer de footer bytes `0x55 0xCC` gedetecteerd worden, wordt `processRadarData()` aangeroepen

### 3. Frame validatie (`isValidFrame`)
Elk frame wordt gevalideerd op:
- Exacte lengte van 30 bytes
- Correcte header: `0xAA 0xFF 0x03 0x00`
- Correcte footer: `0x55 0xCC`

Ongeldige frames worden direct weggegooid.

### 4. Data verwerking (`processRadarData`)

**Ruwe bytes uitlezen:**
- x_raw = byte[4] + byte[5] * 256
- y_raw = byte[6] + byte[7] * 256

**X-coördinaat decodering:**
- x_raw < 32768  →  x_mm = x_raw          (rechterkant, positief)
- x_raw >= 32768 →  x_mm = -(x_raw - 32768)  (linkerkant, negatief)

**Y-coördinaat decodering:**
- y_mm = y_raw - 32768
- Frames waarbij `y_mm <= 0` worden geskipt (geen target voor de sensor).

**Berekeningen:**
$$\text{afstand} = \frac{\sqrt{x_{mm}^2 + y_{mm}^2}}{10} \text{ cm}$$

$$\text{hoek} = \arctan2(x_{mm},\ y_{mm}) \times \frac{180}{\pi} \text{ graden}$$
---

### 5. MQTT Verzending
De data wordt als CSV-string gepubliceerd op topic `vj/radar`:

x_mm,y_mm,afstand_cm,hoek_graden

Voorbeeld:

727,2034,214.7,19.7

---

## Richting referentie

| Positie | Hoek |
|---------|------|
| Recht voor de sensor | 0° |
| Rechterkant | Positieve graden (+) |
| Linkerkant | Negatieve graden (-) |

---

## Serial Monitor output
Bij een geldige meting zie je:

Afstand: 214.7 cm  |  Hoek: 19.7 deg  |  Snelheid: 0 cm/s
MQTT verstuurd: 727,2034,214.7,19.7





