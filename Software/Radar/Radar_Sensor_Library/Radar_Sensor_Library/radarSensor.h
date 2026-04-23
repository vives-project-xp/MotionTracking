#ifndef RADARSENSOR_H
#define RADARSENSOR_H

#include <Arduino.h>

struct RadarTarget {
  float angle;     // Graden (-60 tot 60)
  float distance;  // Afstand in mm
  float x;
  float y;
  bool detected;
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