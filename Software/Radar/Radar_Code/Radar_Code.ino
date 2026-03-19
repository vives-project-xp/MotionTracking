#include <WiFi.h>
#include <PubSubClient.h>
#include <radarSensor.h>

// --- JOUW INSTELLINGEN ---
const char* ssid = "devbit";
const char* password = "Dr@@dloos!";
const char* mqtt_server = "10.20.10.18"; // IP van je PC (of Pi) waar de broker draait

WiFiClient espClient;
PubSubClient client(espClient);
RadarSensor radar(19, 18);

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

void reconnect() {
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT...");
    if (client.connect("ESP32_Radar")) {
      Serial.println("Verbonden");
    } else {
      Serial.print("Mislukt, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  radar.begin();
  Serial.println("Radar gestart.");
}

void loop() {
  if (!client.connected()) { reconnect(); }
  client.loop();

  if (radar.update()) {
    RadarTarget tgt = radar.getTarget();
    if (tgt.detected) {
      // Maak een string: "hoek,afstand"
      String payload = String(tgt.angle) + "," + String(tgt.distance);
      client.publish("vj/radar", payload.c_str());
      Serial.println(payload);
    } else {
      client.publish("vj/radar", "0,0"); // Geef door dat er niemand is
    }
  }
  delay(20); 
}