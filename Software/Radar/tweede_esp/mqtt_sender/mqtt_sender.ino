#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"
// --- 1. WiFi & MQTT Instellingen ---

const char* ssid = SECRET_SSID;          
const char* password = SECRET_PASS;      
const char* mqtt_server = SECRET_MQTT_SERVER; 

WiFiClient espClient;
PubSubClient client(espClient);

// --- 2. UART Pinnen voor de ESP32-C3 ---
// We gebruiken Hardware Serial1. 
// TX gaat naar pin 4 (jouw wens), RX stellen we in op pin 5 (niet direct nodig, maar vereist voor setup)
#define RX_PIN 5
#define TX_PIN 21

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

  Serial.println("");
  Serial.println("WiFi verbonden.");
  Serial.print("IP adres: ");
  Serial.println(WiFi.localIP());
}

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
}

void reconnect() {
  // Blijf proberen tot we verbonden zijn
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT broker...");
    // Geef de client een unieke naam, bijv "ESP32C3_Radar"
    if (client.connect("ESP32C3_Radar1")) {
      Serial.println("verbonden!");
      
      // Abonneer op het topic uit de screenshot
      client.subscribe("vj/radar");
      
    } else {
      Serial.print("mislukt, rc=");
      Serial.print(client.state());
      Serial.println(" probeer opnieuw over 5 seconden");
      delay(5000);
    }
  }
}

void setup() {
  // Serial0 (USB) instellen voor de Serial Monitor in Arduino IDE
  Serial.begin(115200);

  // Serial1 instellen voor de communicatie met de Arduino Uno
  // Baudrate op 9600 is veilig en stabiel voor SoftwareSerial op de Uno
  Serial1.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);

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