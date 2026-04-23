#include <WiFi.h>
#include <PubSubClient.h>
#include <radarSensor.h>

// --- JOUW INSTELLINGEN ---
const char* ssid = "devbit";
const char* password = "$2a$12$sAutUZSpJ39a3N3K/xF8eerg4KuSuQvitPb1BbLg/8U60n5rJxgua";
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
  // Standaard Serial voor PC/Debugging
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
      // Converteer hoek van graden naar radialen (nodig voor C++ cos/sin functies)
      float angleRad = tgt.angle * (PI / 180.0);
      
      // Bereken X en Y
      float x = tgt.x;
      float y = tgt.y;
      
      // Z-as is afhankelijk van je radar. Standaard 2D radars hebben dit niet.
      float z = 0.0; 

      // Maak de string voor de Arduino: "X,Y,Z,angle,distance"
      String payload1 = String(x, 2) + "," + String(y, 2);
      String payload2 = String(tgt.angle) + "," + String(tgt.distance);
      
      client.publish("vj/radar_servo", payload1.c_str());
      Serial.println("MQTT1: " + payload1);
      client.publish("vj/radar", payload2.c_str());
      Serial.println("MQTT2: " + payload2);
      
    } else {
      // Niemand gedetecteerd
      client.publish("vj/radar_servo", "0,0"); 
      client.publish("vj/radar", "0,0"); 
    }
  }
  delay(20); 
}