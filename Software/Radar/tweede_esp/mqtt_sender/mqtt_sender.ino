#include <WiFi.h>
#include <PubSubClient.h>

// --- JOUW INSTELLINGEN ---
const char* ssid = "devbit";
const char* password = "Dr@@dloos!";
const char* mqtt_server = "10.20.10.18"; // IP van je MQTT broker

// --- PINNEN VOOR ARDUINO COMMUNICATIE ---
#define ARDUINO_RX_PIN 5 // Ontvangen van Arduino (optioneel)
#define ARDUINO_TX_PIN 4 // Verzenden naar Arduino (Verbind met Pin 10 op Uno)

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Verbinden met ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi verbonden!");
}

// Deze functie wordt aangeroepen zodra er een nieuw MQTT bericht is
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // 1. Print naar Seriële Monitor (voor debugging op je PC)
  Serial.print("MQTT Ontvangen op [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // 2. Stuur de string direct door naar de Arduino Uno via Serial1
  // We gebruiken println() zodat de Arduino weet wanneer de regel klaar is (\n)
  Serial1.println(message); 
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT...");
    // Let op: Elke MQTT client moet een UNIEKE naam hebben!
    if (client.connect("ESP32_Radar_Ontvanger")) {
      Serial.println("Verbonden");
      
      // Abonneer op het topic met de servo data (X,Y,Z,angle,distance)
      client.subscribe("vj/radar_servo");
    } else {
      Serial.print("Mislukt, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  // Standaard Serial voor PC/Debugging
  Serial.begin(115200);
  
  // Start Serial1 voor de communicatie met de Arduino Uno.
  // We zetten deze op 9600 baud omdat de SoftwareSerial van de Uno dat beter aankan.
  Serial1.begin(9600, SERIAL_8N1, ARDUINO_RX_PIN, ARDUINO_TX_PIN);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  // Koppel de callback functie zodat we berichten kunnen ontvangen
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) { 
    reconnect(); 
  }
  
  // Zorgt ervoor dat inkomende MQTT berichten worden verwerkt
  client.loop();
}