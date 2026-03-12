#include <radarSensor.h>

// ESP32 RX=19, TX=18 (Verbind Sensor TX met 19 en Sensor RX met 18)
RadarSensor radar(19, 18); 

void setup() {
  // Zet de Serial monitor op 115200 om de tekst te lezen
  Serial.begin(115200);
  
  // Start de radar (gebruikt intern 256000 baud)
  radar.begin();
  
  Serial.println("Radar gestart. Wachten op data...");
}

void loop() {
  // Update geeft true als er een volledig pakketje is verwerkt
  if (radar.update()) {
    RadarTarget tgt = radar.getTarget();

    if (tgt.detected) {
      // Stuur ALLEEN de hoek naar de Serial Plotter
      // De plotter verwacht een getal gevolgd door een nieuwe regel (\n)
      Serial.println(tgt.angle);
    }
  }
  
  // We houden de delay laag voor een vloeiende lijn in de plotter
  delay(10); 
}