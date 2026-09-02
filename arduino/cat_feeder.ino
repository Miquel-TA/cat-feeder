/**
 * Cat Feeder Arduino Nano sketch.
 *
 * Receives newline-delimited commands over serial (115200 baud)
 * and activates one of five motors for configurable durations.
 */

#include <Arduino.h>

const int MOTOR_PINS[5] = {3, 5, 6, 9, 10};
const unsigned long MOTOR_DURATION_MS[5] = {1500, 2000, 2500, 3000, 4000};

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 5; i++) {
    pinMode(MOTOR_PINS[i], OUTPUT);
    digitalWrite(MOTOR_PINS[i], LOW);
  }
  Serial.println("Cat feeder ready");
}

void triggerMotor(int index) {
  if (index < 0 || index >= 5) {
    return;
  }
  unsigned long duration = MOTOR_DURATION_MS[index];
  int pin = MOTOR_PINS[index];
  digitalWrite(pin, HIGH);
  delay(duration);
  digitalWrite(pin, LOW);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command == "MOTOR1") {
      triggerMotor(0);
    } else if (command == "MOTOR2") {
      triggerMotor(1);
    } else if (command == "MOTOR3") {
      triggerMotor(2);
    } else if (command == "MOTOR4") {
      triggerMotor(3);
    } else if (command == "MOTOR5") {
      triggerMotor(4);
    }
  }
}
