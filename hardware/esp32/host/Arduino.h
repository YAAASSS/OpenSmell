#pragma once
#include <algorithm>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <iostream>
#include <string>

constexpr int OUTPUT = 1;
constexpr int INPUT_PULLDOWN = 2;
constexpr int LOW = 0;
constexpr int HIGH = 1;
extern int hostInputs[64];
inline int digitalRead(int pin) { return hostInputs[pin]; }
extern unsigned long hostMillis;
extern int hostPins[64];
inline void digitalWrite(int pin, int value) { hostPins[pin] = value; }
inline unsigned long millis() { return hostMillis; }
inline void pinMode(int, int) {}
inline void analogWrite(int pin, int value) { hostPins[pin] = value; }
template <typename T> T constrain(T x, T low, T high) {
  return std::max(low, std::min(x, high));
}
class FakeSerial {
 public:
  std::string input;
  size_t position = 0;
  void begin(int) {}
  int available() { return static_cast<int>(input.size() - position); }
  int read() { return static_cast<unsigned char>(input[position++]); }
  size_t write(uint8_t c) { std::cout.put(static_cast<char>(c)); return 1; }
  size_t write(const uint8_t* data, size_t size) {
    std::cout.write(reinterpret_cast<const char*>(data), size); return size;
  }
  void println() { std::cout << '\n'; }
};
extern FakeSerial Serial;
