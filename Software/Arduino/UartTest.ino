#include <SoftwareSerial.h>

// --- PIN CONFIGURATIE ---
// RX (Ontvangen): Pin 10 (Verbinden met TX Pin 4 van de ESP32)
// TX (Verzenden): Pin 8  (Verbinden met RX Pin 5 van de ESP32)
SoftwareSerial espSerial(10, 8); 

void setup() {
  // Start de monitor op 9600 baud.
  // BELANGRIJK: Zet de Seriële Monitor rechtsonder in de Arduino IDE ook op 9600!
  Serial.begin(9600);

  while (!Serial) { ; }

  // Start de communicatie met de ESP32 op 9600 baud.
  espSerial.begin(9600);

  Serial.println("\n--- Arduino Uno Filter-Ontvanger ---");
  Serial.println("Wachten op gefilterde data van ESP32...");
}

void loop() {
  // Controleer of er data beschikbaar is van de ESP32
  if (espSerial.available() > 0) {
    // We lezen de bytes één voor één uit om corruptie te minimaliseren
    char c = espSerial.read();

    // FILTER: We printen alleen leesbare ASCII karakters
    // 32 is de spatie, 126 is de '~'. Alles daartussen zijn letters, cijfers en punten.
    // We laten ook 10 (\n) en 13 (\r) door voor nieuwe regels.
    if ((c >= 32 && c <= 126) || c == 10 || c == 13) {
      Serial.print(c);
    }
  }

  // Een hele kleine pauze om SoftwareSerial de tijd te geven
  delay(1);
}