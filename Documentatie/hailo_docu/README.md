Hier is een versie van de documentatie, geschreven in een chille en duidelijke studentenstijl (ideaal voor een verslag of README op je eigen GitHub). Ik heb er netjes in verwerkt dat je de basis van de officiële Hailo-repo hebt gehaald en wat je zelf hebt toegevoegd.

Projectverslag: Live Pose Estimation & ArUco Tracking met Hailo-8L
Student: [Je Naam]

Opleiding: [Je Opleiding]

Broncode basis: hailo-ai/hailo-apps (GitHub) (voorheen onderdeel van de hailo-rpi5-examples software stack).

1. Inleiding & Doel
Voor dit project heb ik een applicatie gebouwd die live videobeelden van een camera (/dev/video0) analyseert op een Raspberry Pi 5 met een Hailo-8L AI-kit. Het doel is om zowel de lichaamshouding (pose) van personen als specifieke fysieke markers (ArUco codes) in de ruimte te tracken.

De basis van de GStreamer-pipeline en de AI-verwerking is overgenomen uit de officiële voorbeelden van Hailo. Deze code heb ik vervolgens zelf uitgebreid met computervisie (OpenCV) en een netwerkkoppeling (MQTT) om de verzamelde data bruikbaar te maken voor andere systemen.

2. Wat heb ik overgenomen? (De Basis)
De basisstructuur van de applicatie leunt op de officiële Hailo-infrastructuur. Ik maak gebruik van hun Python-framework voor de Raspberry Pi 5 om de NPU (Neural Processing Unit) aan te sturen.

Pipeline: De klasse GStreamerPoseEstimationApp komt rechtstreeks uit de hailo-apps repository. Dit zorgt ervoor dat het YOLO-gebaseerde pose estimation model hardware-versneld op de Hailo-8L chip draait.

Frames uitlezen: De helper-functies get_caps_from_pad en get_numpy_from_buffer worden gebruikt om de video-frames efficiënt uit de GStreamer-buffer te trekken zonder prestatieverlies.

3. Wat heb ik zelf aangepast/toegevoegd?
Omdat de standaard code van Hailo de beelden alleen lokaal verwerkt (en vaak op een scherm toont), heb ik de code omgebouwd naar een headless applicatie (app.video_sink = "fakesink") die data streamt. Ik heb de volgende features zelf toegevoegd in de app_callback:

3.1 OpenCV ArUco Marker Tracking
Ik heb de cv2.aruco bibliotheek geïntegreerd om te zoeken naar ArUco-markers uit de DICT_4X4_50 set.

De code filtert specifiek op Marker ID 0 tot en met 3.

Als er een marker wordt gevonden, bereken ik het exacte middelpunt.

Dit middelpunt wordt genormaliseerd (gedeeld door de breedte en hoogte van het frame). Hierdoor zijn de coördinaten altijd een waarde tussen 0.0 en 1.0, wat handig is voor schaalbaarheid.

3.2 Data Extractie & Normalisatie van Landmarks
In plaats van de hele pose (alle 17 skeletpunten) te gebruiken, filtert mijn code specifiek op drie belangrijke punten: de neus (p[0]), de linkerhand (p[9]) en de rechterhand (p[10]).
Omdat Hailo deze punten relatief ten opzichte van de bounding box (het vlak om de persoon heen) teruggeeft, reken ik ze in mijn code eerst om naar absolute pixels en normaliseer ik ze daarna naar het volledige beeldformaat.

3.3 MQTT Integratie
Tot slot heb ik paho.mqtt.client toegevoegd. Alle verzamelde data (zowel de locaties van de mensen als de markers) wordt netjes verpakt in een JSON-payload en in real-time gepubliceerd naar de MQTT-broker op 10.20.10.18 onder het topic vj/hailo.

4. Structuur van de Data (JSON Output)
Het uiteindelijke JSON-bericht dat mijn aangepaste code naar de broker stuurt, ziet er zo uit:

JSON
{
  "people": [
    {
      "nose": [0.512, 0.341],
      "left_hand": [0.452, 0.612],
      "right_hand": [0.581, 0.599]
    }
  ],
  "markers": {
    "0": [0.154, 0.822],
    "3": [0.742, 0.211]
  }
}
5. Conclusie
Door de krachtige AI-infrastructuur van de Hailo-apps repository te combineren met handmatige OpenCV-scripts en MQTT, is het gelukt om een efficiënte sensor-node te maken. De zware AI-berekeningen worden door de Hailo NPU opgevangen, waardoor er op de Raspberry Pi 5 genoeg rekenkracht overblijft voor de ArUco-detectie en de netwerkcommunicatie.