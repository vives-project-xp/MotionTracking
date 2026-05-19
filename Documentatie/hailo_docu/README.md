# Documentatie: Werking van de Hailo AI

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
