#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <secrets.h>

#define RX_PIN 19
#define TX_PIN 18
#define BAUD_RATE 256000

uint8_t RX_BUF[64] = {0};
uint8_t RX_count = 0;
uint8_t RX_temp = 0;

const char* ssid = SECRET_SSID;          
const char* password = SECRET_PASS;      
const char* mqtt_server = SECRET_MQTT_SERVER; 

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

    Serial.println("");
    Serial.println("WiFi verbonden.");
    Serial.print("IP adres: ");
    Serial.println(WiFi.localIP());
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Verbinden met MQTT broker...");
        if (client.connect("ESP32C3_Radar")) {
            Serial.println("verbonden!");
            client.subscribe("vj/radar");
        } else {
            Serial.print("mislukt, rc=");
            Serial.print(client.state());
            Serial.println(" probeer opnieuw over 5 seconden");
            delay(5000);
        }
    }
}

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
}

void processRadarData() {
    // Check 1: komt de functie überhaupt binnen?
    Serial.println("processRadarData aangeroepen");

    if (!isValidFrame()) {
        Serial.println("Frame ongeldig!");
        memset(RX_BUF, 0x00, sizeof(RX_BUF));
        RX_count = 0;
        return;
    }

    uint16_t x_raw   = RX_BUF[4]  + RX_BUF[5]  * 256;
    uint16_t y_raw   = RX_BUF[6]  + RX_BUF[7]  * 256;
    uint16_t spd_raw = RX_BUF[8]  + RX_BUF[9]  * 256;

    int16_t x_mm;
    if (x_raw < 32768) {
        x_mm = (int16_t)x_raw;                          // rechts → positief
    } else {
        x_mm = (int16_t)(-(int32_t)(x_raw - 32768));    // links → negatief
    }
    int16_t y_mm  = (int16_t)(y_raw - 32768);
    int16_t speed = 0 - (int16_t)spd_raw;

    // Check 2: wat zijn de ruwe waarden?
    Serial.print("x_raw="); Serial.print(x_raw);
    Serial.print(" y_raw="); Serial.print(y_raw);
    Serial.print(" x_mm="); Serial.print(x_mm);
    Serial.print(" y_mm="); Serial.println(y_mm);

    if (y_mm <= 0) {
        Serial.println("y_mm <= 0, frame geskipt");
        memset(RX_BUF, 0x00, sizeof(RX_BUF));
        RX_count = 0;
        return;
    }

    float distance_cm = sqrt(pow(x_mm, 2) + pow(y_mm, 2)) / 10.0;
    float angle_deg   = atan2(x_mm, y_mm) * 180.0 / PI;

    Serial.print("Afstand: ");
    Serial.print(distance_cm, 1);
    Serial.print(" cm  |  Hoek: ");
    Serial.print(angle_deg, 1);
    Serial.print(" deg  |  Snelheid: ");
    Serial.print(speed);
    Serial.println(" cm/s");
    Serial.print("x_raw="); Serial.print(x_raw);
    Serial.print(" y_raw="); Serial.print(y_raw);
    Serial.print(" x_mm="); Serial.print(x_mm);
    Serial.print(" y_mm="); Serial.print(y_mm);
    Serial.print(" hoek="); Serial.println(angle_deg);

    String payload1 = String(x_mm) + "," + String(y_mm) + "," + String(distance_cm) + "," + String(angle_deg);
    client.publish("vj/radar", payload1.c_str());
    Serial.println("MQTT verstuurd: " + payload1);

    memset(RX_BUF, 0x00, sizeof(RX_BUF));
    RX_count = 0;
}
// Zet dit even in en kijk wat de Serial Monitor zegt dan weten we exact waar het stopt!

void setup() {
    Serial.begin(115200);
    Serial1.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
    Serial1.setRxBufferSize(64);

    Serial1.write(Single_Target_Detection_CMD, sizeof(Single_Target_Detection_CMD));
    delay(200);
    Serial.println("Radar gestart.");

    RX_count = 0;
    Serial1.flush();

    setup_wifi();
    client.setServer(mqtt_server, 1883);
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

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
