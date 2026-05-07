# Research
> Hier vindt men alle research die we gedaan hebben

## Eventuele opstelling
- 1x Beamer om visuals te projecteren
- 1x Raspberry Pi 5 voor dherkenning en uitsturen van beeld
- Eigen gemaakte moving-head/spot (2x servomotoren, Spotlamp, drivers, ESP32(of andere)) die de artiest zal volgen
- 1x radar sensor om de artiest precieser te kunnen volgen

# Research - Radar Sensor

## Doel van het project
Het doel van het project is om één of meerdere artiesten te volgen met een licht.

---

## Sensorkeuze

### Waarom de RD-03D?
We hebben direct gekozen voor de Ai-Thinker RD-03D mmWave radar. Deze sensor had twee grote voordelen die voor ons project belangrijk waren:

- **Nauwkeurige tracking**: De sensor volgt een persoon heel precies.
- **Onderscheid tussen mens en object**: De sensor heeft een ingebouwd library dat het verschil kan zien tussen een mens en een gewoon object.

Een nadeel is dat de sensor heel gevoelig is. Hij pikt dus snel bewegingen op, wat goed is voor tracking maar ook betekent dat er veel ruismetingen kunnen binnenkomen.

---

## Bronnen

De belangrijkste bronnen die we gebruikt hebben:

- **Officiële datasheet** van Ai-Thinker: hierin vonden we het frame formaat, de standaard baudrate (256000 bps) en de elektrische specificaties deze kan je vinden onder de map Research > Datasheets > Ai-Thinker Rd-03D 24GHz Radar Sensor Module_Datasheet.pdf
- **Artikel van Electronic Clinic**: [Real-time Human Tracking Radar with mmWave Sensor and ESP32-S3 Touchscreen](https://www.electroniclinic.com/real-time-human-tracking-radar-with-mmwave-sensor-and-esp32-s3-touchscreen/)

Via het artikel hebben we een code gevonden die frames van de sensor stuurt, hoe de berekeningen voor de hoek werken en hoe we de correcte `x_mm` en `y_mm` waarden konden berekenen uit de ruwe bytes.

---

## Bevindingen

### Wat werkte goed
De tracking zelf werkt heel goed. De sensor detecteert een persoon snel als hij beweegt en volgt die vloeiend. De nauwkeurigheid is voldoende voor gebruik op een podium.

### Problemen
Het grootste probleem dat we tegenkwamen was dat veel van de binnengekomen frames incorrect waren. De sensor stuurt namelijk ook frames zonder nuttige data. Hiervoor hebben we een filter geschreven die elk frame valideert door de header (`0xAA 0xFF 0x03 0x00`) en footer (`0x55 0xCC`) te controleren, en frames met een ongeldige Y-waarde te negeren.

De decoding van de X-coördinaat was ook niet meteen duidelijk. Via trial and error met de ruwe data hebben we uiteindelijk de correcte formule gevonden:
- **Rechterkant** (positief): `x_mm = x_raw` wanneer `x_raw < 32768`
- **Linkerkant** (negatief): `x_mm = -(x_raw - 32768)` wanneer `x_raw >= 32768`

---

## Technische keuzes

| Keuze | Reden |
|-------|-------|
| **ESP32** | Heeft ingebouwde WiFi, nodig voor communicatie |
| **WiFi** | Meest praktisch voor draadloze communicatie op een podium |
| **MQTT** | Makkelijk protocol zodat alle componenten van het project met elkaar kunnen communiceren |



