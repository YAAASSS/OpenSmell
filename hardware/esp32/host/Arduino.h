#pragma once
#include <algorithm>
#include <cmath>
#include <cstring>
#include <cstdint>
#include <iostream>
#include <string>

constexpr int OUTPUT = 1;
extern unsigned long hostMillis;
extern int hostPins[64];
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
