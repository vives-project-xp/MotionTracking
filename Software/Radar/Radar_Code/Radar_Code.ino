#include <WiFi.h>
#include <PubSubClient.h>
#include <RD03D.h>

// ============================================================
//  INSTELLINGEN
// ============================================================
const char* ssid        = "devbit";
const char* password    = "Dr@@dloos!";
const char* mqtt_server = "10.20.10.18";

#define RADAR_RX 19
#define RADAR_TX 18

// ============================================================
//  FILTER & LOCK PARAMETERS
// ============================================================
#define MAX_TRACKED      3        // Max bijgehouden personen
#define LOCK_TIMEOUT_MS  10000   // Hoe lang een persoon bijgehouden wordt zonder nieuw signaal (ms)
#define SMOOTHING        0.25f   // Low-pass factor: 0.0 = nooit updaten, 1.0 = geen filter
                                  // 0.25 = 25% nieuw signaal, 75% vorige waarde → soepele beweging
#define ANGLE_MAX        80.0f   // Maximale hoek in graden (±80°)
#define MATCH_RADIUS_MM  400     // Afstand (mm) waarbinnen een nieuwe meting als "dezelfde persoon" geldt
#define PUBLISH_INTERVAL 80      // MQTT publish interval in ms

// ============================================================
//  DATASTRUCTUUR PER BIJGEHOUDEN PERSOON
// ============================================================
struct TrackedPerson {
  bool    active;          // Is deze slot in gebruik?
  float   x;               // Gefilterde X positie (mm)
  float   y;               // Gefilterde Y positie (mm)
  float   angle;           // Berekende hoek (graden)
  float   distance;        // Berekende afstand (mm)
  unsigned long lastSeen;  // Timestamp laatste detectie (ms)
  uint8_t missedFrames;    // Aantal frames niet gezien
};

TrackedPerson tracked[MAX_TRACKED];

// ============================================================
//  OBJECTEN
// ============================================================
WiFiClient   espClient;
PubSubClient client(espClient);
RD03D        radar(RADAR_RX, RADAR_TX);

// ============================================================
//  WIFI & MQTT
// ============================================================
void setup_wifi() {
  Serial.print("Verbinden met ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi verbonden! IP: " + WiFi.localIP().toString());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT... ");
    if (client.connect("ESP32_Radar")) {
      Serial.println("Verbonden!");
    } else {
      Serial.print("Mislukt, rc=");
      Serial.print(client.state());
      Serial.println(" – opnieuw over 2s");
      delay(2000);
    }
  }
}

// ============================================================
//  HULPFUNCTIES
// ============================================================

// Clamp hoek naar ±ANGLE_MAX graden
float clampAngle(float angle) {
  if (angle >  ANGLE_MAX) return  ANGLE_MAX;
  if (angle < -ANGLE_MAX) return -ANGLE_MAX;
  return angle;
}

// Afstand tussen twee punten (mm)
float pointDistance(float x1, float y1, float x2, float y2) {
  return sqrt(sq(x1 - x2) + sq(y1 - y2));
}

// Zoek de dichtstbijzijnde actieve tracked persoon voor punt (x, y)
// Geeft -1 terug als geen match binnen MATCH_RADIUS_MM
int findClosestPerson(float x, float y) {
  int   bestIdx  = -1;
  float bestDist = MATCH_RADIUS_MM;

  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].active) continue;
    float d = pointDistance(tracked[i].x, tracked[i].y, x, y);
    if (d < bestDist) {
      bestDist = d;
      bestIdx  = i;
    }
  }
  return bestIdx;
}

// Zoek een vrije slot
int findFreeSlot() {
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].active) return i;
  }
  return -1;
}

// Verwijder personen die te lang niet gezien zijn
void expireOldPersons() {
  unsigned long now = millis();
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (tracked[i].active && (now - tracked[i].lastSeen > LOCK_TIMEOUT_MS)) {
      Serial.printf("Persoon %d verlopen (niet gezien voor %lu ms)\n", i + 1, LOCK_TIMEOUT_MS);
      tracked[i].active = false;
    }
  }
}

// Update of maak een nieuwe tracked persoon aan met gefilterde waarden
void updateTracking(float rawX, float rawY) {

  // Bereken hoek en filter meteen
  float rawAngle    = atan2((float)rawY, (float)rawX) * 180.0f / PI;
  float rawDistance = sqrt(sq(rawX) + sq(rawY));

  // Hoek buiten bereik? Negeer meting
  if (rawAngle > ANGLE_MAX || rawAngle < -ANGLE_MAX) return;

  int idx = findClosestPerson(rawX, rawY);

  if (idx >= 0) {
    // Bestaande persoon: low-pass filter toepassen
    tracked[idx].x        = tracked[idx].x * (1.0f - SMOOTHING) + rawX * SMOOTHING;
    tracked[idx].y        = tracked[idx].y * (1.0f - SMOOTHING) + rawY * SMOOTHING;
    tracked[idx].angle    = clampAngle(atan2(tracked[idx].y, tracked[idx].x) * 180.0f / PI);
    tracked[idx].distance = sqrt(sq(tracked[idx].x) + sq(tracked[idx].y));
    tracked[idx].lastSeen = millis());

  } else {
    // Nieuwe persoon
    idx = findFreeSlot();
    if (idx < 0) {
      Serial.println("Geen vrije slot! Max personen bereikt.");
      return;
    }
    tracked[idx].active   = true;
    tracked[idx].x        = rawX;
    tracked[idx].y        = rawY;
    tracked[idx].angle    = clampAngle(rawAngle);
    tracked[idx].distance = rawDistance;
    tracked[idx].lastSeen = millis();
    Serial.printf("Nieuwe persoon gedetecteerd in slot %d\n", idx + 1);
  }
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  // Alle slots leegmaken
  for (int i = 0; i < MAX_TRACKED; i++) {
    tracked[i].active = false;
  }

  setup_wifi();
  client.setServer(mqtt_server, 1883);

  bool ok = radar.initialize(RD03D::MULTI_TARGET);
  Serial.println(ok ? "Radar gestart (multi-target)." : "Radar init MISLUKT!");
}

// ============================================================
//  LOOP
// ============================================================
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

<<<<<<< HEAD
  // Radar frame ophalen
  radar.tasks();

  // Verwijder verlopen personen
  expireOldPersons();

  // Verwerk nieuwe radardata
  uint8_t count = radar.getTargetCount();
  for (int i = 0; i < MAX_TRACKED; i++) {
    TargetData* tgt = radar.getTarget(i);
    if (tgt != nullptr && tgt->isValid()) {
      // Gebruik de ruwe X en Y uit de library (in mm)
      updateTracking((float)tgt->x, (float)tgt->y);
=======
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
>>>>>>> 48900817d9c9b56eed3615f07ab75e09382294da
    }
  }

  // MQTT publishen op interval
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish < PUBLISH_INTERVAL) return;
  lastPublish = millis();

  bool anyActive = false;

  for (int i = 0; i < MAX_TRACKED; i++) {
    String baseTopic = "vj/radar/persoon" + String(i + 1);

    if (tracked[i].active) {
      anyActive = true;

      float angle    = tracked[i].angle;
      float distance = tracked[i].distance;
      float x        = tracked[i].x;
      float y        = tracked[i].y;

      // Payload voor spotlight/servo: "X,Y,Z,angle,distance"
      String payloadServo = String(x, 1) + "," + String(y, 1) + ",0," +
                            String(angle, 1) + "," + String(distance, 1);

      // Simpele payload: "angle,distance"
      String payloadSimple = String(angle, 1) + "," + String(distance, 1);

      client.publish((baseTopic + "_servo").c_str(), payloadServo.c_str());
      client.publish(baseTopic.c_str(), payloadSimple.c_str());

      Serial.printf("Persoon %d: hoek=%.1f°  afstand=%.0fmm  X=%.0f Y=%.0f\n",
                    i + 1, angle, distance, x, y);
    } else {
      // Stuur 0 als persoon niet actief
      client.publish(baseTopic.c_str(), "0,0");
      client.publish((baseTopic + "_servo").c_str(), "0,0,0,0,0");
    }
  }

  if (!anyActive) {
    Serial.println("Niemand gedetecteerd.");
  }
}
