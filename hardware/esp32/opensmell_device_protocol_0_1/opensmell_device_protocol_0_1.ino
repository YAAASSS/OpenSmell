#include <ArduinoJson.h>

const int OUTPUT_PIN = 23;

const char* PROTOCOL_VERSION = "0.1";
const char* DEVICE_ID = "opensmell-esp32-led-001";

const int DEVICE_CHANNEL = 0;

const float MIN_INTENSITY = 0.0;
const float MAX_INTENSITY = 1.0;

const float MIN_DURATION = 0.1;
const float MAX_DURATION = 30.0;

// Prototype-specific serial framing limit.
//
// This is a constraint of this ESP32 implementation,
// not a universal OpenSmell Device Protocol limit.
//
// One byte is reserved for the terminating '\0'.
const size_t MAX_SERIAL_MESSAGE_BYTES = 1024;

// Current rendering state.
bool rendering = false;
unsigned long renderStartedAt = 0;
unsigned long renderDurationMs = 0;

// Current serial receive state.
char serialBuffer[MAX_SERIAL_MESSAGE_BYTES + 1];
size_t serialLength = 0;
bool serialMessageTooLong = false;


// --------------------------------------------------
// Physical output
// --------------------------------------------------

void setIntensity(float intensity) {
  intensity = constrain(intensity, 0.0, 1.0);

  // Convert OpenSmell intensity 0.0-1.0 to PWM 0-255.
  int pwmValue = round(intensity * 255.0);

  analogWrite(OUTPUT_PIN, pwmValue);
}


void stopRendering() {
  setIntensity(0.0);

  rendering = false;
  renderStartedAt = 0;
  renderDurationMs = 0;
}


// --------------------------------------------------
// OpenSmell responses
// --------------------------------------------------

void sendError(const char* code, const char* message) {
  JsonDocument response;

  response["protocol_version"] = PROTOCOL_VERSION;
  response["type"] = "error";
  response["code"] = code;
  response["message"] = message;

  serializeJson(response, Serial);
  Serial.println();
}


void sendOk() {
  JsonDocument response;

  response["protocol_version"] = PROTOCOL_VERSION;
  response["type"] = "ok";

  serializeJson(response, Serial);
  Serial.println();
}


void sendHello() {
  JsonDocument response;

  response["protocol_version"] = PROTOCOL_VERSION;
  response["type"] = "hello_response";
  response["device_id"] = DEVICE_ID;

  serializeJson(response, Serial);
  Serial.println();
}


void sendCapabilities() {
  JsonDocument response;

  response["protocol_version"] = PROTOCOL_VERSION;
  response["type"] = "capabilities";
  response["device_id"] = DEVICE_ID;

  JsonArray channels = response["channels"].to<JsonArray>();

  JsonObject channel = channels.add<JsonObject>();

  channel["channel"] = DEVICE_CHANNEL;
  channel["min_intensity"] = MIN_INTENSITY;
  channel["max_intensity"] = MAX_INTENSITY;

  response["min_duration"] = MIN_DURATION;
  response["max_duration"] = MAX_DURATION;

  serializeJson(response, Serial);
  Serial.println();
}


// --------------------------------------------------
// OpenSmell render handling
// --------------------------------------------------

void handleRender(JsonDocument& request) {

  if (!request["duration"].is<float>() &&
      !request["duration"].is<int>() &&
      !request["duration"].is<double>()) {

    sendError(
      "invalid_plan",
      "duration must be a number"
    );

    return;
  }

  float duration = request["duration"];

  if (duration < MIN_DURATION || duration > MAX_DURATION) {

    sendError(
      "invalid_plan",
      "duration outside device capabilities"
    );

    return;
  }

  if (!request["commands"].is<JsonArray>()) {

    sendError(
      "invalid_plan",
      "commands must be an array"
    );

    return;
  }

  JsonArray commands = request["commands"];

  float targetIntensity = 0.0;

  for (JsonObject command : commands) {

    if (!command["channel"].is<int>()) {

      sendError(
        "invalid_plan",
        "channel must be an integer"
      );

      return;
    }

    int channel = command["channel"];

    if (channel != DEVICE_CHANNEL) {

      sendError(
        "unsupported_channel",
        "device only supports channel 0"
      );

      return;
    }

    if (!command["intensity"].is<float>() &&
        !command["intensity"].is<int>() &&
        !command["intensity"].is<double>()) {

      sendError(
        "invalid_plan",
        "intensity must be a number"
      );

      return;
    }

    float intensity = command["intensity"];

    if (intensity < MIN_INTENSITY ||
        intensity > MAX_INTENSITY) {

      sendError(
        "invalid_plan",
        "intensity outside device capabilities"
      );

      return;
    }

    targetIntensity = intensity;
  }


  // Start rendering.
  setIntensity(targetIntensity);

  renderStartedAt = millis();
  renderDurationMs =
      (unsigned long)(duration * 1000.0);

  rendering = true;


  // OpenSmell receives confirmation immediately.
  // The device does not wait for the rendering
  // duration to complete before responding.
  sendOk();
}


// --------------------------------------------------
// Protocol message handling
// --------------------------------------------------

void handleMessage(const char* line) {

  JsonDocument request;

  DeserializationError error =
      deserializeJson(request, line);

  if (error) {

    sendError(
      "invalid_json",
      "unable to parse JSON message"
    );

    return;
  }


  if (!request["protocol_version"].is<const char*>()) {

    sendError(
      "invalid_message",
      "protocol_version missing"
    );

    return;
  }


  const char* version =
      request["protocol_version"];

  if (strcmp(version, PROTOCOL_VERSION) != 0) {

    sendError(
      "unsupported_protocol_version",
      "only protocol version 0.1 is supported"
    );

    return;
  }


  if (!request["type"].is<const char*>()) {

    sendError(
      "invalid_message",
      "type missing"
    );

    return;
  }


  const char* type = request["type"];


  if (strcmp(type, "hello") == 0) {

    sendHello();
    return;
  }


  if (strcmp(type, "get_capabilities") == 0) {

    sendCapabilities();
    return;
  }


  if (strcmp(type, "render") == 0) {

    handleRender(request);
    return;
  }


  sendError(
    "unknown_message_type",
    "unsupported message type"
  );
}


// --------------------------------------------------
// Serial framing
// --------------------------------------------------

void resetSerialMessage() {
  serialLength = 0;
  serialMessageTooLong = false;
}


void finishSerialMessage() {

  if (serialMessageTooLong) {

    sendError(
      "message_too_large",
      "serial message exceeds device limit"
    );

    resetSerialMessage();
    return;
  }


  if (serialLength == 0) {
    resetSerialMessage();
    return;
  }


  // Ignore an optional carriage return from CRLF framing.
  if (
    serialLength > 0 &&
    serialBuffer[serialLength - 1] == '\r'
  ) {
    serialLength--;
  }


  if (serialLength == 0) {
    resetSerialMessage();
    return;
  }


  serialBuffer[serialLength] = '\0';

  handleMessage(serialBuffer);

  resetSerialMessage();
}


void receiveSerialMessages() {

  while (Serial.available() > 0) {

    char incoming =
        (char)Serial.read();


    // Newline completes one protocol frame.
    if (incoming == '\n') {

      finishSerialMessage();
      continue;
    }


    // Once the frame is known to be too large,
    // discard bytes until the terminating newline.
    if (serialMessageTooLong) {
      continue;
    }


    if (serialLength >= MAX_SERIAL_MESSAGE_BYTES) {

      serialMessageTooLong = true;
      continue;
    }


    serialBuffer[serialLength] = incoming;
    serialLength++;
  }
}


// --------------------------------------------------
// Arduino
// --------------------------------------------------

void setup() {

  pinMode(OUTPUT_PIN, OUTPUT);

  stopRendering();

  Serial.begin(115200);

  resetSerialMessage();

  // Do not emit arbitrary text here.
  // SerialDeviceTransport expects protocol
  // responses only.
}


void loop() {

  // Stop rendering automatically without blocking
  // serial communication.
  if (rendering) {

    unsigned long elapsed =
        millis() - renderStartedAt;

    if (elapsed >= renderDurationMs) {
      stopRendering();
    }
  }


  // One OpenSmell JSON message per line.
  //
  // Reception is incremental and bounded so a malformed
  // or untrusted peer cannot make the device allocate an
  // arbitrarily large String before a newline is received.
  receiveSerialMessages();
}