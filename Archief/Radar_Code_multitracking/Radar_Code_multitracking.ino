#include <WiFi.h>
#include <PubSubClient.h>
#include <RD03D.h>

// ============================================================
//  INSTELLINGEN
// ============================================================
const char* ssid        = "devbit";
const char* password    = "";
const char* mqtt_server = "10.20.10.18";

#define RADAR_RX 19
#define RADAR_TX 18


// ============================================================
//  PARAMETERS
// ============================================================
#define MAX_TRACKED       3
#define LOCK_TIMEOUT_MS   30000  // 30s → slot vrijgeven
#define FREEZE_TIMEOUT_MS 2000   // 2s niet gezien → 0,0 sturen
#define SMOOTHING         0.25f
#define ANGLE_MAX         80.0f
#define MATCH_RADIUS_MM   400
#define PUBLISH_INTERVAL  80
#define MIN_DISTANCE_MM   500    // Dichter dan 50cm = ongeldig (reflecties)
#define MAX_DISTANCE_MM   6000   // Verder dan 6m = ongeldig
#define MIN_Y_MM          200    // Y moet positief zijn (voor de sensor)
#define MIN_DIST_RES      50     // Minimum distanceRes voor betrouwbare meting
#define SMOOTHING         0.15f  // Rustiger dan 0.25
#define MATCH_RADIUS_MM   600    // Groter voor langere afstanden

// ============================================================
//  PER PERSOON
// ============================================================
struct TrackedPerson {
  bool          active;
  bool          locked;
  float         x;
  float         y;
  float         angle;
  float         distance;
  unsigned long lastSeen;
  unsigned long lockedAt;
};

TrackedPerson tracked[MAX_TRACKED];

// MQTT topics per persoon (zelfde als origineel)
const char* topicSimple[MAX_TRACKED] = {
  "vj/radar/persoon1",
  "vj/radar/persoon2",
  "vj/radar/persoon3"
};
const char* topicServo[MAX_TRACKED] = {
  "vj/radar/persoon1_servo",
  "vj/radar/persoon2_servo",
  "vj/radar/persoon3_servo"
};

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
  Serial.println("\nWiFi verbonden!");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Verbinden met MQTT... ");
    if (client.connect("ESP32_Radar")) {
      Serial.println("Verbonden!");
    } else {
      Serial.print("Mislukt, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

// ============================================================
//  HULPFUNCTIES
// ============================================================
float calcAngle(float x, float y) {
  float angle = atan2(-x, y) * 180.0f / PI;
  if (angle >  ANGLE_MAX) return  ANGLE_MAX;
  if (angle < -ANGLE_MAX) return -ANGLE_MAX;
  return angle;
}

float pointDistance(float x1, float y1, float x2, float y2) {
  return sqrt(sq(x1 - x2) + sq(y1 - y2));
}

int findClosest(float x, float y) {
  int   bestIdx  = -1;
  float bestDist = MATCH_RADIUS_MM;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].active || !tracked[i].locked) continue;
    float d = pointDistance(tracked[i].x, tracked[i].y, x, y);
    if (d < bestDist) {
      bestDist = d;
      bestIdx  = i;
    }
  }
  return bestIdx;
}

int findFreeSlot() {
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].active) return i;
  }
  return -1;
}

// ============================================================
//  LOCK BEHEER
// ============================================================
void checkLocks() {
  unsigned long now = millis();
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!tracked[i].active) continue;
    if (now - tracked[i].lockedAt > LOCK_TIMEOUT_MS) {
      Serial.printf("Persoon %d: 30s verlopen → slot vrijgegeven\n", i + 1);
      tracked[i].active = false;
      tracked[i].locked = false;
    }
  }
}

// ============================================================
//  TRACKING UPDATE
// ============================================================
void updateTracking(float rawX, float rawY, uint16_t distRes) {

  // --- FILTERS ---

  // 1. distanceRes te laag → onbetrouwbare meting
  if (distRes < MIN_DIST_RES) return;

  // 2. Y moet positief zijn (voor de sensor)
  if (rawY < MIN_Y_MM) return;

  // 3. Afstand berekenen en controleren
  float rawDistance = sqrt(sq(rawX) + sq(rawY));
  if (rawDistance < MIN_DISTANCE_MM || rawDistance > MAX_DISTANCE_MM) return;

  // 4. Hoek berekenen en clampen
  float rawAngle = atan2(-rawX, rawY) * 180.0f / PI;
  if (rawAngle > ANGLE_MAX || rawAngle < -ANGLE_MAX) return;

  // --- TRACKING ---
  unsigned long now = millis();
  int idx = findClosest(rawX, rawY);

  if (idx >= 0) {
    tracked[idx].x        = tracked[idx].x * (1.0f - SMOOTHING) + rawX * SMOOTHING;
    tracked[idx].y        = tracked[idx].y * (1.0f - SMOOTHING) + rawY * SMOOTHING;
    tracked[idx].angle    = calcAngle(tracked[idx].x, tracked[idx].y);
    tracked[idx].distance = sqrt(sq(tracked[idx].x) + sq(tracked[idx].y));
    tracked[idx].lastSeen = now;
  } else {
    idx = findFreeSlot();
    if (idx < 0) return;
    tracked[idx].active   = true;
    tracked[idx].locked   = true;
    tracked[idx].x        = rawX;
    tracked[idx].y        = rawY;
    tracked[idx].angle    = rawAngle;
    tracked[idx].distance = rawDistance;
    tracked[idx].lastSeen = now;
    tracked[idx].lockedAt = now;
    Serial.printf("Persoon %d gelockt! hoek: %.1f°  afstand: %.0fmm\n",
                  idx + 1, rawAngle, rawDistance);
  }
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  for (int i = 0; i < MAX_TRACKED; i++) {
    tracked[i].active = false;
    tracked[i].locked = false;
  }

  setup_wifi();
  client.setServer(mqtt_server, 1883);

  bool ok = radar.initialize(RD03D::MULTI_TARGET);
  Serial.println(ok ? "Radar gestart (multi-target)." : "Radar init MISLUKT!");
}

// ============================================================
//  LOOP
// ============================================================
// Vervang de loop() door dit:

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  radar.tasks();
  checkLocks();

  // Verzamel alle frames binnen 100ms window
  static float   sumX[RD03D::MAX_TARGETS]    = {0};
  static float   sumY[RD03D::MAX_TARGETS]    = {0};
  static uint32_t sumRes[RD03D::MAX_TARGETS] = {0};  // nieuw
  static int     count[RD03D::MAX_TARGETS]   = {0};

  for (int i = 0; i < RD03D::MAX_TARGETS; i++) {
    TargetData* tgt = radar.getTarget(i);
    if (tgt != nullptr && tgt->isValid()) {
      sumX[i]   += tgt->x;
      sumY[i]   += tgt->y;
      sumRes[i] += tgt->distanceRes;  // nieuw
      count[i]  += 1;
    }
  }

// Na 100ms window:
  for (int i = 0; i < RD03D::MAX_TARGETS; i++) {
    if (count[i] > 0) {
      float    avgX   = sumX[i]   / count[i];
      float    avgY   = sumY[i]   / count[i];
      uint16_t avgRes = sumRes[i] / count[i];  // nieuw
      updateTracking(avgX, avgY, avgRes);       // nieuw
    }
    sumX[i]   = 0;
    sumY[i]   = 0;
    sumRes[i] = 0;  // nieuw
    count[i]  = 0;
  }

    // MQTT publishen
    for (int i = 0; i < MAX_TRACKED; i++) {
      bool visible = tracked[i].active &&
                     tracked[i].locked &&
                     (millis() - tracked[i].lastSeen <= FREEZE_TIMEOUT_MS);

      if (visible) {
        String payloadSimple = String(tracked[i].angle, 1) + "," + String(tracked[i].distance, 1);
        String payloadServo  = String(tracked[i].x, 1) + "," + String(tracked[i].y, 1) + ",0," +
                               String(tracked[i].angle, 1) + "," + String(tracked[i].distance, 1);

        client.publish(topicSimple[i], payloadSimple.c_str());
        client.publish(topicServo[i],  payloadServo.c_str());

        Serial.printf("Persoon %d → %.1f°  %.0fmm\n", i + 1, tracked[i].angle, tracked[i].distance);
      } else {
        client.publish(topicSimple[i], "0,0");
        client.publish(topicServo[i],  "0,0,0,0,0");
      }
    }
  }
