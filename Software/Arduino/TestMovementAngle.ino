// ----------------------------------------------------
// PAN–TILT TEST CODE (NO ESP32 REQUIRED)
// Type an angle into Serial Monitor and press Enter
// ----------------------------------------------------

#define Y_STEP_PIN    3
#define Y_DIR_PIN     6

#define Z_STEP_PIN    4
#define Z_DIR_PIN     7

#define ENABLE_PIN    8
#define LIMIT_PIN     9   // NC switch → LOW = not hit, HIGH = hit

int fastDelay = 1200;
int slowDelay = 3000;

// -------------------------------
// POSITION TRACKING + LIMITS
// -------------------------------
long yPosition = 0;
const long Y_MAX = 1000;

// -------------------------------
// Z ROTATION SETTINGS
// -------------------------------
const float STEPS_PER_REV = 12000.0;  
const float STEPS_PER_DEG = STEPS_PER_REV / 360.0;

float currentAngle = 0;


// ----------------------------------------------------
// SETUP
// ----------------------------------------------------
void setup() {
  Serial.begin(9600);

  Serial.println("\n--- PAN–TILT TEST MODE ---");
  Serial.println("Type an angle (0–360) and press Enter.");
  Serial.println("Example: 45");

  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN, OUTPUT);

  pinMode(Z_STEP_PIN, OUTPUT);
  pinMode(Z_DIR_PIN, OUTPUT);

  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(LIMIT_PIN, INPUT_PULLUP);

  digitalWrite(ENABLE_PIN, LOW);

  delay(300);
  homeAxis();
}


// ----------------------------------------------------
// MAIN LOOP — READ ANGLES FROM SERIAL
// ----------------------------------------------------
void loop() {

  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.length() == 0) return;

    float angle = line.toFloat();

    Serial.print("Command received: ");
    Serial.println(angle);

    rotateZToAngle(angle);
  }
}


// ----------------------------------------------------
// Y STEP WITH SOFT LIMIT
// ----------------------------------------------------
void stepOnceY(int d) {

  if (digitalRead(Y_DIR_PIN) == HIGH && yPosition >= Y_MAX) {
    Serial.println("Y soft limit reached.");
    return;
  }

  digitalWrite(Y_STEP_PIN, HIGH);
  delayMicroseconds(d);
  digitalWrite(Y_STEP_PIN, LOW);
  delayMicroseconds(d);

  if (digitalRead(Y_DIR_PIN) == HIGH) yPosition++;
  else yPosition--;
}


// ----------------------------------------------------
// HOMING ROUTINE FOR TILT AXIS
// ----------------------------------------------------
void homeAxis() {
  Serial.println("Homing start...");

  digitalWrite(Y_DIR_PIN, LOW);

  while (digitalRead(LIMIT_PIN) == LOW) {
    stepOnceY(fastDelay);
  }

  Serial.println("Switch hit.");

  digitalWrite(Y_DIR_PIN, HIGH);

  for (int i = 0; i < 200; i++) {
    stepOnceY(fastDelay);
  }

  Serial.println("Backed off 200 steps.");

  digitalWrite(Y_DIR_PIN, LOW);

  for (int i = 0; i < 180; i++) {
    stepOnceY(slowDelay);
  }

  Serial.println("Final home position reached.");

  yPosition = 0;
}


// ----------------------------------------------------
// Z AXIS: MOVE TO TARGET ANGLE (0–360°, shortest path)
// ----------------------------------------------------
void rotateZToAngle(float targetAngle) {

  // Normalize target angle
  while (targetAngle < 0)   targetAngle += 360;
  while (targetAngle >= 360) targetAngle -= 360;

  float delta = targetAngle - currentAngle;

  // Shortest path logic
  if (delta > 180)  delta -= 360;
  if (delta < -180) delta += 360;

  int steps = abs(delta) * STEPS_PER_DEG;

  if (steps == 0) return;

  if (delta > 0) digitalWrite(Z_DIR_PIN, HIGH);
  else           digitalWrite(Z_DIR_PIN, LOW);

  for (int i = 0; i < steps; i++) {
    digitalWrite(Z_STEP_PIN, HIGH);
    delayMicroseconds(1200);
    digitalWrite(Z_STEP_PIN, LOW);
    delayMicroseconds(1200);
  }

  currentAngle = targetAngle;

  Serial.print("Z moved to angle: ");
  Serial.println(currentAngle);
}
