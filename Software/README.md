# Software
> Hier vindt men alle software




# Ai-Thinker RD-03D Radar Software
## Hoe de software werkt

### 1. Data Ontvangst
De sensor stuurt pakketjes van **30 bytes**. De software controleert eerst de header (`0xAA 0xFF 0x03 0x00`) om te bevestigen dat het om een geldig datapakket gaat voordat de verwerking begint.

### 2. Bit-Conversie (Bit-Masking)
De ruwe X- en Y-waardes worden uit de bytes samengevoegd. Omdat de sensor een specifieke methode gebruikt voor negatieve getallen (waarbij bit 15 het teken is), passen we een masker toe:
* **Waarde**: Bits 0 t/m 14 ($xRaw \& 0x7FFF$).
* **Teken (+/-)**: Bit 15 ($xRaw \& 0x8000$).

### 3. Wiskundige Berekening
De software rekent de X- en Y-coördinaten om naar bruikbare poolcoördinaten:
* **Afstand**: Berekend met de stelling van Pythagoras: $$\text{afstand} = \sqrt{x^2 + y^2}$$
* **Hoek**: Berekend met de `atan2(x, abs(y))` functie om de hoek in graden te krijgen ten opzichte van het midden ($0^\circ$ is recht vooruit).

### 4. Filters (De "Guardrails")
Om te voorkomen dat de plotter "springt" of valse meldingen geeft bij stilstand, moet een target aan deze eisen voldoen:
1. **Minimale Afstand**: Moet $\ge 500$ mm zijn (filtert reflecties van de behuizing/tafel).
2. **Gezichtsveld**: Moet tussen $-60^\circ$ en $+60^\circ$ liggen.

---

## Gebruik in de Arduino IDE

1. Open de **Serial Plotter** (`Ctrl` + `Shift` + `L`).
2. Zet de baudrate onderin op **115.200**.
3. Je ziet nu een stabiele lijn. 
   * Beweeg je naar links? De lijn gaat naar positieve graden.
   * Beweeg je naar rechts? De lijn gaat naar negatieve graden.
   * Ben je te dichtbij (< 50cm)? Dan zal het een output van 0,0 geven.

---

## Bestandsstructuur
* `radarSensor.h`: Bevat de definities van de `RadarTarget` struct en de klasse functies.
* `radarSensor.cpp`: De "motor" van de library waar de bytes worden omgezet naar wiskundige locaties.
* `project.ino`: De hoofcode die de library aanroept en de resultaten naar de computer stuurt.

### Project Structuur
```text
 Software/
└── Radar/
    ├── Radar_Sensor_Library.zip
    │   ├── radarSensor.cpp
    │   └── radarSensor.h
    └── Radar_Code/
        └── project.ino

