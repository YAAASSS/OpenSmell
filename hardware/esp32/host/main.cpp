// Execute the actual sketch with a fake clock, serial port and PWM outputs.
// This host harness cannot access GPIO, serial devices or physical actuators.
#include <Arduino.h>
#include "../opensmell_device_protocol_0_1/opensmell_device_protocol_0_1.ino"
#include <iostream>
#include <string>

FakeSerial Serial;
unsigned long hostMillis = 0;
int hostPins[64] = {};

int main() {
  setup();
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.rfind("!advance ", 0) == 0) {
      hostMillis += std::stoul(line.substr(9));
      loop();
      std::cout << "{\"host\":\"advanced\"}\n";
    } else if (line == "!pins") {
      std::cout << "{\"host_pwm\":[" << hostPins[23] << ","
                << hostPins[22] << "," << hostPins[21] << "]}\n";
    } else {
      Serial.input = line + "\n";
      Serial.position = 0;
      loop();
    }
    std::cout.flush();
  }
}
