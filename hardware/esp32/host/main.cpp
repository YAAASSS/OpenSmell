// Execute the actual sketch with a fake clock, serial port and PWM outputs.
// This host harness cannot access GPIO, serial devices or physical actuators.
#include <Arduino.h>
#include "../opensmell_device_protocol_0_1/opensmell_device_protocol_0_1.ino"
#include <iostream>
#include <string>
#include <chrono>

FakeSerial Serial;
unsigned long hostMillis = 0;
int hostPins[64] = {};

int main(int argc, char** argv) {
  bool realtime = false;
#ifdef OPENSMELL_EXPERIMENTAL_LIFECYCLE
  if (argc == 2 && std::string(argv[1]) == "--realtime") realtime = true;
  else if (argc != 1) return 2;
#else
  (void)argv;
  if (argc != 1) return 2;
#endif
  auto started = std::chrono::steady_clock::now();
  setup();
  std::string line;
  while (std::getline(std::cin, line)) {
    if (realtime) hostMillis = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();
    if (line.rfind("!advance ", 0) == 0) {
      if (realtime) return 2;
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
