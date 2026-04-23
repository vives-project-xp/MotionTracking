#include "radarSensor.h"

RadarSensor::RadarSensor(int8_t rx, int8_t tx) : _rx(rx), _tx(tx) {
  _serial = &Serial1;
}

void RadarSensor::begin() {
  _serial->begin(256000, SERIAL_8N1, _rx, _tx);
}

bool RadarSensor::update() {
  if (_serial->available() >= 30) {
    uint8_t head[4];
    _serial->readBytes(head, 4);

    if (head[0] == 0xAA && head[1] == 0xFF && head[2] == 0x03 && head[3] == 0x00) {
      uint8_t data[26];
      _serial->readBytes(data, 26);

      // Raw data van Target 1
      int16_t xRaw = data[0] | (data[1] << 8);
      int16_t yRaw = data[2] | (data[3] << 8);

      // Bit-maskering voor negatieve getallen (Sign-bit op bit 15)
      float x = (xRaw & 0x7FFF) * ((xRaw & 0x8000) ? -1 : 1);
      float y = (yRaw & 0x7FFF) * ((yRaw & 0x8000) ? -1 : 1);

      // Bereken de absolute afstand en hoek
      // We gebruiken abs(y) voor de check voor het geval de sensor negatieve waarden stuurt
      float afstand = sqrt(x*x + y*y);
      float berekendeHoek = atan2(x, abs(y)) * (180.0 / PI); // abs(y) fixeert de hoek naar voren

      // STRENG FILTEREN:
      // We checken de totale AFSTAND (mm) in plaats van alleen de Y-as
      if (afstand >= 500.0 && afstand <= 6000.0 && berekendeHoek >= -60.0 && berekendeHoek <= 60.0) {
        _target.detected = true;
        _target.angle = berekendeHoek;
        _target.distance = afstand;
        _target.x = x;
        _target.y = y;
      } else {
        _target.detected = false;
        _target.angle = 0; 
        _target.distance = 0;
      }
      return true;
    }
  }
  return false;
}

RadarTarget RadarSensor::getTarget() {
  return _target;
}