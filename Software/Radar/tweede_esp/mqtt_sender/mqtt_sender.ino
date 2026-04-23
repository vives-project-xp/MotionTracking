#include <WiFi.h>
#include <PubSubClient.h>

// --- INSTELLINGEN ---
const char* ssid = "devbit";
const char* password = "Dr@@dloos!";
const char* mqtt_server = "10.20.10.18"; 

// --- PINNEN VOOR UNO ---
#define ARDUINO_RX_PIN 5 
#define ARDUINO_TX_PIN 4 

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("\nWiFi verbinden...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK!");
}

void callback(char* topic, byte* payload, unsigned int length) {
  // We maken het bericht leeg en vullen het met de binnengekomen tekens
  String message = "";
  for (int i = 0; i < length; i++) {
    char c = (char)payload[i];
    // Filter: Alleen leesbare tekens toevoegen (cijfers, punten, komma's, letters)
    if (isPrintable(c)) {
      message += c;
    }
  }

  String topicStr = String(topic);

  // --- HIER GEBEURT HET FILTEREN ---
  
  if (topicStr.endsWith("persoon1_servo")) {
    Serial.print("Persoon 1 gedetecteerd: ");
    Serial.println(message);
    Serial1.print("P1:"); 
    Serial1.println(message); // Stuur naar Uno
  } 
  else if (topicStr.endsWith("persoon2_servo")) {
    Serial.print("Persoon 2 gedetecteerd: ");
    Serial.println(message);
    Serial1.print("P2:"); 
    Serial1.println(message); // Stuur naar Uno
  } 
  else if (topicStr.endsWith("persoon3_servo")) {
    Serial.print("Persoon 3 gedetecteerd: ");
    Serial.println(message);
    Serial1.print("P3:"); 
    Serial1.println(message); // Stuur naar Uno
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("MQTT verbinding zoeken...");
    String clientId = "ESP32_Radar_Final_" + String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("VERBONDEN!");
      
      // We abonneren op de hele map 'vj/radar/'
      client.subscribe("vj/radar/#");
      
      Serial.println("Filter actief op: vj/radar/...");
    } else {
      Serial.print("Fout rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

void setup() {
  // PC Monitor op 115200
  Serial.begin(115200); 
  
  // Uno Communicatie op 9600
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