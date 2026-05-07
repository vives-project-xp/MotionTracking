# Software
> Hier vindt men alle software

# Ai-Thinker RD-03D Radar Software

## Hoe de software werkt

### 1. Data Ontvangst
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

### 2. Coördinaat Decodering
De ruwe X- en Y-waardes worden samengesteld via little-endian optelling:
**X-coördinaat (links/rechts):**
De sensor gebruikt een gedeeld bereik rond 32768 (2¹⁵):
- Rechterkant (positief): `x_raw < 32768` → `x_mm = x_raw`
- Linkerkant (negatief): `x_raw >= 32768` → `x_mm = -(x_raw - 32768)`

**Y-coördinaat (afstand voorwaarts):**
$$y_{mm} = y_{raw} - 32768$$

---

### 3. Wiskundige Berekening
De software rekent de X- en Y-coördinaten om naar poolcoördinaten:

**Afstand** via de stelling van Pythagoras:
$$\text{afstand} = \frac{\sqrt{x_{mm}^2 + y_{mm}^2}}{10} \text{ cm}$$

**Hoek** via atan2:
$$\text{hoek} = \arctan2(x_{mm},\ y_{mm}) \times \frac{180}{\pi} \text{ graden}$$

Waarbij $0°$ recht vooruit is voor de radar, positieve graden rechts en negatieve graden links.

---

### 4. Filters
Om ongeldige frames te verwijderen:
1. **Frame lengte**: Exact 30 bytes.
2. **Header & footer**: Moeten exact overeenkomen.
3. **Y-waarde**: Moet groter zijn dan 0 (target moet voor de sensor staan).

---

### 5. MQTT Verzending
Na een geldige meting wordt de data via WiFi gepubliceerd op het MQTT topic `vj/radar` als CSV-string:

---


### Gebruik in de Arduino IDE

1. Stel jouw **WiFi credentials** in bovenaan de code.
2. Stel het correcte **MQTT broker IP-adres** in (`mqtt_server`).
3. Upload de code naar de ESP32.
4. Open de **Serial Monitor** (`Ctrl` + `Shift` + `L`) op **115200 baud**.
5. De ESP32 verbindt automatisch met WiFi en de MQTT broker.
6. Je ziet nu serial output zoals:

**Afstand: 214.7 cm  |  Hoek: 19.7 deg  |  Snelheid: 0 cm/s**

---

**Richting referentie:**
- Beweeg je naar **links**? → Hoek gaat naar **negatieve** graden.
- Beweeg je naar **rechts**? → Hoek gaat naar **positieve** graden.
- Recht voor de sensor = **0°**.

---

## Bestandsstructuur

```text
Software/
└── Radar/
    └── Radar_Code/
        └── Radar_Code.ino
```
---

## Gebruikte Libraries

| Library | Functie | Installatie |
|---------|---------|-------------|
| `WiFi.h` | WiFi verbinding | Ingebouwd in ESP32 core |
| `PubSubClient.h` | MQTT communicatie | Via Arduino Library Manager |
| `Arduino.h` | Arduino basis | Ingebouwd |