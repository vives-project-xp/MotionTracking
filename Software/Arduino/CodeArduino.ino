#include <NeoSWSerial.h>

// NeoSWSerial: RX=2, TX=3 — do NOT use pin 2 or 3 for anything else
NeoSWSerial espSerial(2, 3);

// ----------------------------------------------------
// UART BUFFER
// ----------------------------------------------------
#define UART_BUFFER_SIZE 64
char uartBuffer[UART_BUFFER_SIZE];
int  uartIndex = 0;

// ----------------------------------------------------
// PINS  (Y_STEP was 3 — conflicted with espSerial RX!)
// ----------------------------------------------------
#define Y_STEP_PIN  3
#define Y_DIR_PIN   6

#define Z_STEP_PIN  4
#define Z_DIR_PIN   7

#define ENABLE_PIN  8
#define LIMIT_PIN   9      // NC wiring: LOW = free, HIGH = triggered

// ----------------------------------------------------
// STEPPER CONFIG
// ----------------------------------------------------
#define STEPS_PER_REV   14000
#define STEPS_PER_DEG   (STEPS_PER_REV / 360.0f)

#define PULSE_WIDTH_US  800

// How often (µs) each axis gets one step batch
#define INTERVAL_Y_US   1500
#define INTERVAL_Z_US   1500

// Y travel limits (steps)
#define Y_MAX_STEPS     2200
#define Y_MIN_STEPS     600

// Z angle limits
#define Z_MIN_ANGLE    -90.0f
#define Z_MAX_ANGLE     90.0f

// Dead-zones — stop hunting when close enough
#define Z_DEADZONE      2.0f
#define Y_DEADZONE      2

// Homing backoff distance
#define HOME_BACKOFF    700

// Steps moved per scheduler tick (non-blocking batches)
#define Y_STEPS_PER_TICK  5     // reduced — fewer steps per tick = more loop() turns
#define Z_STEPS_PER_TICK  1     // one degree per tick; increase if pan is too slow

// ----------------------------------------------------
// STATE
// ----------------------------------------------------
long  currentY    = 700;
long  targetY     = 700;

float currentAngle = 0.0f;
float targetAngle  = 0.0f;

unsigned long lastStepY = 0;
unsigned long lastStepZ = 0;

// ----------------------------------------------------
// FORWARD DECLARATIONS
// ----------------------------------------------------
void homeAxis();
void updateMotors();
void processPacket(char* line);
float extractField(char* s, int fieldIndex);
void stepY(int direction);
void stepZ(int direction);

// ====================================================
void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);

  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN,  OUTPUT);
  pinMode(Z_STEP_PIN, OUTPUT);
  pinMode(Z_DIR_PIN,  OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(LIMIT_PIN,  INPUT_PULLUP);

  digitalWrite(ENABLE_PIN, LOW);   // enable drivers

  delay(300);
  homeAxis();

  Serial.println("System ready.");
}

// ====================================================
void loop() {
  // --- Drain serial, build line ---
  while (espSerial.available()) {
    char c = espSerial.read();

    if (c == '\n' || c == '\r') {
      if (uartIndex > 0) {
        uartBuffer[uartIndex] = '\0';
        processPacket(uartBuffer);
        uartIndex = 0;
      }
    } else if (uartIndex < UART_BUFFER_SIZE - 1) {
      uartBuffer[uartIndex++] = c;
    }
  }

  updateMotors();
}

// ====================================================
// PACKET PARSING
// Format: x,y,distance,angle
// ====================================================
void processPacket(char* line) {
  float dist  = extractField(line, 2);   // 3rd field
  float angle = extractField(line, 3);   // 4th field

  // ---- Z axis (pan) ----
  if (angle > -9000.0f) {                // sentinel check
    angle = constrain(angle, Z_MIN_ANGLE, Z_MAX_ANGLE);
    targetAngle = angle;
  }

  // ---- Y axis (tilt) ----
  if (dist >= 0.0f) {
    dist = constrain(dist, 0.0f, 500.0f);
    targetY = (long)((1.0f - (dist / 500.0f)) * Y_MAX_STEPS);
    targetY = constrain(targetY, (long)Y_MIN_STEPS, (long)Y_MAX_STEPS);
  }
}

// ====================================================
// EXTRACT FIELD  (zero-indexed)
// Returns the numeric value of field[fieldIndex].
// Returns -9999 on failure so callers can detect "not found".
// ====================================================
float extractField(char* s, int fieldIndex) {
  int field = 0;
  int i     = 0;

  while (s[i] != '\0') {
    if (s[i] == ',') {
      field++;
      i++;
      continue;
    }

    if (field == fieldIndex) {
      // Make sure there's at least one digit/sign character
      if (s[i] == '-' || s[i] == '+' || (s[i] >= '0' && s[i] <= '9')) {
        return atof(&s[i]);
      } else {
        return -9999.0f;   // field exists but not numeric
      }
    }
    i++;
  }
  return -9999.0f;   // field not found
}

// ====================================================
// NON-BLOCKING MOTOR SCHEDULER
// Called every loop() iteration; does at most one small
// batch of steps per axis so serial never starves.
// ====================================================
void updateMotors() {
  unsigned long now = micros();

  // ---- Z axis (pan) ----
  float deltaZ = targetAngle - currentAngle;
  if (fabs(deltaZ) > Z_DEADZONE) {
    if (now - lastStepZ >= (unsigned long)INTERVAL_Z_US) {
      lastStepZ = now;
      int dir = (deltaZ > 0) ? 1 : -1;
      // Step multiple degrees if far away (faster slew), but cap to remaining
      int stepsNeeded = (int)(fabs(deltaZ) * STEPS_PER_DEG);
      int stepsThisTick = min(stepsNeeded, (int)(Z_STEPS_PER_TICK * STEPS_PER_DEG));

      digitalWrite(Z_DIR_PIN, dir > 0 ? HIGH : LOW);
      for (int i = 0; i < stepsThisTick; i++) {
        digitalWrite(Z_STEP_PIN, HIGH);
        delayMicroseconds(PULSE_WIDTH_US);
        digitalWrite(Z_STEP_PIN, LOW);
        delayMicroseconds(PULSE_WIDTH_US);   // equal off-time
      }
      // Update angle proportionally
      currentAngle += dir * (stepsThisTick / STEPS_PER_DEG);
    }
  }

  // ---- Y axis (tilt) ----
  long deltaY = targetY - currentY;
  if (abs(deltaY) > Y_DEADZONE) {
    if (now - lastStepY >= (unsigned long)INTERVAL_Y_US) {
      lastStepY = now;
      int dir = (deltaY > 0) ? 1 : -1;

      // Guard against limit switch during normal movement too
      if (dir < 0 && digitalRead(LIMIT_PIN) == HIGH) {
        // Limit hit unexpectedly — re-zero and stop
        currentY = 0;
        targetY  = 0;
        Serial.println("WARN: limit hit outside homing — re-zeroed.");
        return;
      }

      int stepsToMove = min((long)Y_STEPS_PER_TICK, abs(deltaY));

      digitalWrite(Y_DIR_PIN, dir > 0 ? HIGH : LOW);
      for (int i = 0; i < stepsToMove; i++) {
        // Hard software limits
        if (dir > 0 && currentY >= Y_MAX_STEPS) break;
        if (dir < 0 && currentY <= Y_MIN_STEPS) break;

        // Live limit-switch check every step when moving toward home
        if (dir < 0 && digitalRead(LIMIT_PIN) == HIGH) {
          currentY = 0;
          targetY  = 0;
          Serial.println("WARN: limit triggered mid-move.");
          break;
        }

        digitalWrite(Y_STEP_PIN, HIGH);
        delayMicroseconds(PULSE_WIDTH_US);
        digitalWrite(Y_STEP_PIN, LOW);
        delayMicroseconds(PULSE_WIDTH_US);

        currentY += dir;
      }
    }
  }
}

// ====================================================
// HOMING: move toward switch → hit → back off → zero
// ====================================================
void stepOnce(int halfPeriodUs) {
  digitalWrite(Y_STEP_PIN, HIGH);
  delayMicroseconds(halfPeriodUs);
  digitalWrite(Y_STEP_PIN, LOW);
  delayMicroseconds(halfPeriodUs);
}

void homeAxis() {
  Serial.println("Homing...");

  // 1) Creep toward limit switch
  digitalWrite(Y_DIR_PIN, LOW);
  unsigned long startMs = millis();
  while (digitalRead(LIMIT_PIN) == LOW) {
    stepOnce(1200);
    if (millis() - startMs > 10000UL) {   // 10 s timeout
      Serial.println("ERROR: homing timeout — check wiring.");
      return;
    }
  }
  Serial.println("Switch hit.");

  // 2) Back off so carriage is clear of switch
  digitalWrite(Y_DIR_PIN, HIGH);
  for (int i = 0; i < HOME_BACKOFF; i++) {
    stepOnce(1200);
  }
  Serial.println("Homing done.");

  currentY = 0;
  targetY  = 0;
}
