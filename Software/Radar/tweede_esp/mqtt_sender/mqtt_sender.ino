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

// Deze functie wordt aangeroepen zodra er een nieuw MQTT bericht is op een van de topics
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Debugging naar PC monitor
  Serial.print("Bericht op [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // We sturen de data door naar de Arduino Uno.
  // We checken van welk topic het komt om een label mee te sturen
  if (String(topic) == "vj/radar") {
    // Stel dat dit bericht "X:100,Y:200" bevat
    Serial1.println(message); 
  } 
  else if (String(topic) == "vj/radar_servo") {
    // Stel dat dit bericht "A:45" bevat
    // We zorgen dat er altijd een 'A:' label bij staat voor de Uno parser
    if (message.indexOf("A:") == -1) {
      Serial1.print("A:");
    }
    Serial1.println(message);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT...");
    if (client.connect("ESP32_Radar_Ontvanger")) {
      Serial.println("Verbonden");
      
      // ABONNEER OP BEIDE TOPICS
      client.subscribe("vj/radar");       // Voor X en Y data
      client.subscribe("vj/radar_servo"); // Voor de hoek (Angle) data
      
      Serial.println("Geabonneerd op vj/radar en vj/radar_servo");
    } else {
      Serial.print("Mislukt, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  
  // Start Serial1 voor de Uno (9600 baud voor stabiliteit)
  Serial1.begin(9600, SERIAL_8N1, ARDUINO_RX_PIN, ARDUINO_TX_PIN);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) { 
    reconnect(); 
  }
  client.loop();
}