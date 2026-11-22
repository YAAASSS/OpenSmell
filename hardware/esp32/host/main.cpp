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
int hostInputs[64] = {};

int main(int argc, char** argv) {
  bool realtime = false;
#ifdef OPENSMELL_EXPERIMENTAL_LIFECYCLE
  bool simulateEnable = false;
  bool bootEnableHigh = false;
  for (int i=1; i<argc; ++i) {
    const std::string arg(argv[i]);
    if (arg == "--realtime" && !realtime) realtime = true;
#ifdef OPENSMELL_EXPERIMENTAL_DRY_LOAD
    else if (arg == "--simulate-enable" && !simulateEnable) simulateEnable = true;
    else if (arg == "--boot-enable-high" && !bootEnableHigh) bootEnableHigh = true;
#endif
    else return 2;
  }
  if (simulateEnable && bootEnableHigh) return 2;
#ifdef OPENSMELL_EXPERIMENTAL_DRY_LOAD
  if (bootEnableHigh) hostInputs[32] = HIGH;
#endif
#else
  (void)argv;
  if (argc != 1) return 2;
#endif
  auto started = std::chrono::steady_clock::now();
  setup();
#ifdef OPENSMELL_EXPERIMENTAL_DRY_LOAD
  if (simulateEnable) {
    // Explicit fake-input opt-in for installed process clients. Never accesses GPIO.
    hostInputs[32] = LOW; loop();
    hostInputs[32] = HIGH; loop();
  }
#endif
  std::string line;
  while (std::getline(std::cin, line)) {
    if (realtime) hostMillis = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();
    if (line.rfind("!advance ", 0) == 0) {
      if (realtime) return 2;
      hostMillis += std::stoul(line.substr(9));
      loop();
      std::cout << "{\"host\":\"advanced\"}\n";
#ifdef OPENSMELL_EXPERIMENTAL_DRY_LOAD
    } else if (line == "!enable 0" || line == "!enable 1") {
      hostInputs[32] = line.back() == '1' ? HIGH : LOW;
      loop();
      std::cout << "{\"host_enable\":" << (dryArmed ? "true" : "false") << "}\n";
#endif
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
