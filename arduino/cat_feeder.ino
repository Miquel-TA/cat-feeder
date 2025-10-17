/**
 * Cat Feeder Arduino Sketch
 * -------------------------
 * Receives commands over the serial port in the format `MOTOR:<id>`
 * where <id> is 1 through 5. Each motor activates for the configured
 * duration when commanded.
 */

const uint8_t MOTOR_COUNT = 5;
const uint8_t MOTOR_PINS[MOTOR_COUNT] = {2, 3, 4, 5, 6};
const unsigned long MOTOR_DURATION_MS = 1000; // Active time per command

bool motorActive[MOTOR_COUNT] = {false, false, false, false, false};
unsigned long motorDeactivateAt[MOTOR_COUNT] = {0, 0, 0, 0, 0};

String serialBuffer;

void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    pinMode(MOTOR_PINS[i], OUTPUT);
    digitalWrite(MOTOR_PINS[i], LOW);
  }
}

void loop() {
  readSerialCommands();
  updateMotors();
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char incoming = static_cast<char>(Serial.read());
    if (incoming == '\n' || incoming == '\r') {
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += incoming;
    }
  }
}

void processCommand(const String &command) {
  if (command.startsWith("MOTOR:")) {
    int motorId = command.substring(6).toInt();
    triggerMotor(motorId);
  }
}

void triggerMotor(int motorId) {
  if (motorId < 1 || motorId > MOTOR_COUNT) {
    return; // Invalid motor index
  }
  uint8_t index = static_cast<uint8_t>(motorId - 1);
  digitalWrite(MOTOR_PINS[index], HIGH);
  motorActive[index] = true;
  motorDeactivateAt[index] = millis() + MOTOR_DURATION_MS;
}

void updateMotors() {
  unsigned long now = millis();
  for (uint8_t i = 0; i < MOTOR_COUNT; i++) {
    if (motorActive[i] && now >= motorDeactivateAt[i]) {
      digitalWrite(MOTOR_PINS[i], LOW);
      motorActive[i] = false;
    }
  }
}
