#include <Arduino.h>

<<<<<<< HEAD
#define RX_PIN 19
#define TX_PIN 18
#define BAUD_RATE 256000

uint8_t RX_BUF[64] = {0};
uint8_t RX_count = 0;
uint8_t RX_temp = 0;

uint8_t Single_Target_Detection_CMD[12] = {
    0xFD, 0xFC, 0xFB, 0xFA,
    0x02, 0x00, 0x80, 0x00,
    0x04, 0x03, 0x02, 0x01
};

bool isValidFrame() {
    if (RX_count != 30)      return false;
    if (RX_BUF[0]  != 0xAA) return false;
    if (RX_BUF[1]  != 0xFF) return false;
    if (RX_BUF[2]  != 0x03) return false;
    if (RX_BUF[3]  != 0x00) return false;
    if (RX_BUF[28] != 0x55) return false;
    if (RX_BUF[29] != 0xCC) return false;
    return true;
=======
// --- INSTELLINGEN ---
const char* ssid = "devbit";
const char* password = "$2a$12$sAutUZSpJ39a3N3K/xF8eerg4KuSuQvitPb1BbLg/8U60n5rJxgua";
const char* mqtt_server = "10.20.10.18"; // IP van je PC (of Pi) waar de broker draait

WiFiClient espClient;
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
>>>>>>> 2b279d1856dbaa73ef890ba0d104019291083dae
}

void processRadarData() {
    if (!isValidFrame()) {
        memset(RX_BUF, 0x00, sizeof(RX_BUF));
        RX_count = 0;
        return;
    }

    // Decoding volgens het artikel
    uint16_t x_raw = RX_BUF[4] + RX_BUF[5] * 256;
    uint16_t y_raw = RX_BUF[6] + RX_BUF[7] * 256;
    uint16_t spd_raw = RX_BUF[8] + RX_BUF[9] * 256;
    uint16_t res_raw = RX_BUF[10] + RX_BUF[11] * 256;

    int16_t x_mm  = (int16_t)x_raw;          // ← was: 0 - (int16_t)x_raw
    int16_t y_mm  = (int16_t)(y_raw - 32768);
    int16_t speed = 0 - (int16_t)spd_raw;

    float distance_cm = sqrt(pow(x_mm, 2) + pow(y_mm, 2)) / 10.0;
    float angle_deg   = atan2(x_mm, y_mm) * 180.0 / PI;

    // Alleen printen als Y positief is (target voor de sensor)
    if (y_mm <= 0) {
        memset(RX_BUF, 0x00, sizeof(RX_BUF));
        RX_count = 0;
        return;
    }

    Serial.print("Afstand: ");
    Serial.print(distance_cm, 1);
    Serial.print(" cm  |  Hoek: ");
    Serial.print(angle_deg, 1);
    Serial.print(" deg  |  X: ");
    Serial.print(x_mm / 10.0, 1);
    Serial.print(" cm  |  Y: ");
    Serial.print(y_mm / 10.0, 1);
    Serial.print(" cm  |  Snelheid: ");
    Serial.print(speed);
    Serial.println(" cm/s");

    memset(RX_BUF, 0x00, sizeof(RX_BUF));
    RX_count = 0;
}

void setup() {
    Serial.begin(115200);
    Serial1.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
    Serial1.setRxBufferSize(64);

    Serial1.write(Single_Target_Detection_CMD, sizeof(Single_Target_Detection_CMD));
    delay(200);
    Serial.println("Radar gestart.");

    RX_count = 0;
    Serial1.flush();
}

void loop() {
    while (Serial1.available()) {
        RX_temp = Serial1.read();
        RX_BUF[RX_count++] = RX_temp;

        if (RX_count >= sizeof(RX_BUF)) {
            RX_count = sizeof(RX_BUF) - 1;
        }

        if ((RX_count > 1) &&
            (RX_BUF[RX_count - 1] == 0xCC) &&
            (RX_BUF[RX_count - 2] == 0x55)) {
            processRadarData();
        }
    }
}