#include <Arduino.h>

const uint8_t MOTOR_COUNT = 5;
const uint8_t MOTOR_PINS[MOTOR_COUNT] = {2, 3, 4, 5, 6};
const unsigned long MOTOR_DURATION_MS = 1000;

void triggerMotor(uint8_t index) {
  if (index >= MOTOR_COUNT) {
    Serial.print("ERR:INVALID_MOTOR\n");
    return;
  }

  Serial.print("ACK:START:");
  Serial.println(index + 1);

  digitalWrite(MOTOR_PINS[index], HIGH);
  delay(MOTOR_DURATION_MS);
  digitalWrite(MOTOR_PINS[index], LOW);

  Serial.print("ACK:STOP:");
  Serial.println(index + 1);
}

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ;
  }

  for (uint8_t i = 0; i < MOTOR_COUNT; ++i) {
    pinMode(MOTOR_PINS[i], OUTPUT);
    digitalWrite(MOTOR_PINS[i], LOW);
  }

  Serial.println("READY");
}

void loop() {
  if (Serial.available() == 0) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command.startsWith("MOTOR:")) {
    int motorId = command.substring(6).toInt();
    if (motorId <= 0 || motorId > MOTOR_COUNT) {
      Serial.print("ERR:INVALID_MOTOR\n");
    } else {
      triggerMotor(motorId - 1);
    }
  } else if (command.equalsIgnoreCase("PING")) {
    Serial.println("PONG");
  } else if (command.length() > 0) {
    Serial.print("ERR:UNKNOWN_COMMAND:");
    Serial.println(command);
  }
}
