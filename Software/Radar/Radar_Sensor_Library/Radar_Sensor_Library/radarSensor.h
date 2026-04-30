#ifndef RADARSENSOR_H
#define RADARSENSOR_H

#include <Arduino.h>

struct RadarTarget {
    bool detected;
    float x;
    float y;
    float angle;
    float distance;
};

class RadarSensor {
  public:
    RadarSensor(int8_t rx, int8_t tx);
    void begin();
    bool update(); 
    RadarTarget getTarget();

  private:
    HardwareSerial* _serial;
    RadarTarget _target;
    uint8_t _rx, _tx;
};

#endif