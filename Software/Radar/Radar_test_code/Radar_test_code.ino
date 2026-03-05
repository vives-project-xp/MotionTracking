#include <Arduino.h>

#define RX_PIN 19
#define TX_PIN 18
#define BAUD_RATE 256000

uint8_t RX_BUF[64] = {0};
uint8_t RX_count = 0;
uint8_t RX_temp = 0;

// Target data
int16_t target_x = 0, target_y = 0;
int16_t target_speed = 0;
uint16_t target_distance_res = 0;

float target_distance = 0;
float target_angle = 0;

unsigned long lastPrint = 0;
const int refreshRate = 1000; // 1 seconde

uint8_t Single_Target_Detection_CMD[12] = {
0xFD,0xFC,0xFB,0xFA,
0x02,0x00,
0x80,0x00,
0x04,0x03,0x02,0x01
};

void setup()
{
    Serial.begin(115200);
    Serial1.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
    Serial1.setRxBufferSize(64);

    Serial.println("RD-03D Radar Started");

    Serial1.write(Single_Target_Detection_CMD, sizeof(Single_Target_Detection_CMD));

    delay(200);
}

void printDashboard()
{
    Serial.println("====== RD-03D TARGET TRACKING ======");

    Serial.print("Distance: ");
    Serial.print(target_distance / 10.0);
    Serial.println(" cm");

    Serial.print("Angle: ");
    Serial.print(target_angle);
    Serial.println(" deg");

    Serial.print("X: ");
    Serial.print(target_x);
    Serial.println(" mm");

    Serial.print("Y: ");
    Serial.print(target_y);
    Serial.println(" mm");

    Serial.print("Speed: ");
    Serial.print(target_speed);
    Serial.println(" cm/s");

    Serial.println("===============================");
    Serial.println();
}

void processRadarData()
{
    if (RX_count < 16) return;

    target_x = (RX_BUF[4] | (RX_BUF[5] << 8)) - 0x200;
    target_y = (RX_BUF[6] | (RX_BUF[7] << 8)) - 0x8000;
    target_speed = (RX_BUF[8] | (RX_BUF[9] << 8)) - 0x10;
    target_distance_res = (RX_BUF[10] | (RX_BUF[11] << 8));

    target_distance = sqrt(pow(target_x,2) + pow(target_y,2));
    target_angle = atan2(target_y,target_x) * 180.0 / PI;

    memset(RX_BUF,0,sizeof(RX_BUF));
    RX_count = 0;
}

void loop()
{
    while (Serial1.available())
    {
        RX_temp = Serial1.read();
        RX_BUF[RX_count++] = RX_temp;

        if (RX_count >= sizeof(RX_BUF))
            RX_count = sizeof(RX_BUF)-1;

        if ((RX_count>1) && (RX_BUF[RX_count-1]==0xCC) && (RX_BUF[RX_count-2]==0x55))
        {
            processRadarData();
        }
    }

    // print only once per second
    if(millis() - lastPrint > refreshRate)
    {
        lastPrint = millis();
        printDashboard();
    }
}