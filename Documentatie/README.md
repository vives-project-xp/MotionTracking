# Documentatie
> Hier vindt men alle documentatie

# Pan and Tilt Joint
Voor dit project hebben wij een pan and tilt joint gebruikt dat alle richtingen in kan draaien. Hiervoor bestaat all een mooi bestaand project: https://www.thingiverse.com/thing:4316563
We kunnen hier vinden hoedat wij het samen stellen: https://www.youtube.com/watch?v=uJO7mv4-0PY
Voor het grote rollement hebben wij dit ook uitgeprint en met gesmeerd zodat het vlot draait.
Beide Stepper Motors namelijk de NEMA-17 Zijn verbonden met QShield v5d en het shield is verbonden aan de Arduino. Het QShield heeft min 12V nodig We voeden het met een adapter van 12V en 2A, Dit is genoeg voor onze stepper motors. En dan hebben wij deze lamp gemonteerd op het statief: https://www.bax-shop.be/nl/pinspot/eurolite-led-pst-12w-6000k-spot-smalle-beam-pinspot

# Code Pan and Tilt Joint
De code werd geschreven in C in Arduino IDE voor de Arduino Uno dat wij in dit project gebruiken. Je kunt de Code hier vinden: https://github.com/vives-project-xp/MotionTracking/tree/main/Software/Arduino


# Ai-Thinker RD-03D Radar Documentatie

In dit project hebben we gerbuik gemaakt van de **Ai-Thinker RD-03D** (gebaseerd op de LD2450 chip) die gerbuik maakt van een speciale RD-03D library. De software is geoptimaliseerd om stabiele hoek- en afstandsberekeningen te maken en ruis te filteren voor een betrouwbare detectie.

---

## Kenmerken
* **0° Center-Alignment**: De software lijnt 0 graden uit in het midden van de sensor.
* **Smart Filtering**: Detecteert alleen objecten tussen **50 cm** en **6 meter**.
* **Angle Clipping**: Negeert alle "ghost" detecties buiten het gezichtsveld van **-60° tot +60°**.
* **Bit-Masking**: Correcte verwerking van de 15-bit sign-data specifiek voor de RD-03D/LD2450 firmware.

---

## Aansluitschema (ESP32 DEV build)

| RD-03D Pin | ESP32 Pin | Beschrijving |
| :--- | :--- | :--- |
| **1 (VCC)** | 5V | Voeding  |
| **2 (GND)** | GND | Massa / Ground |
| **3 (TX)** | GPIO 19 | Seriële data Ontvangst (Verbind met RX op ESP) |
| **4 (RX)** | GPIO 18 | Seriële data Verzending (Verbind met TX op ESP) |

> **Belangrijk:** De sensor communiceert op **115.200 baud**, wat storingsgevoelig is over lange afstanden.



