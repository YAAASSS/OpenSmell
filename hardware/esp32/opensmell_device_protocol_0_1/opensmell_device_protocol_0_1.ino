#include <ArduinoJson.h>


// --------------------------------------------------
// Physical device configuration
// --------------------------------------------------

const int CHANNEL_COUNT = 3;

const int CHANNEL_PINS[CHANNEL_COUNT] = {
  23,  // OpenSmell channel 0
  22,  // OpenSmell channel 1
  21   // OpenSmell channel 2
};

const char* PROTOCOL_VERSION = "0.1";
const char* DEVICE_ID = "opensmell-esp32-led-3ch-001";

const float MIN_INTENSITY = 0.0;
const float MAX_INTENSITY = 1.0;

const float MIN_DURATION = 0.1;
const float MAX_DURATION = 30.0;


// --------------------------------------------------
// Serial framing configuration
// --------------------------------------------------

// Prototype-specific serial framing limit.
//
// This is a constraint of this ESP32 implementation,
// not a universal OpenSmell Device Protocol limit.
//
// One byte is reserved for the terminating '\0'.
const size_t MAX_SERIAL_MESSAGE_BYTES = 1024;


// --------------------------------------------------
// Rendering state
// --------------------------------------------------

bool rendering = false;

unsigned long renderStartedAt = 0;
unsigned long renderDurationMs = 0;


// --------------------------------------------------
// Serial receive state
// --------------------------------------------------

char serialBuffer[MAX_SERIAL_MESSAGE_BYTES + 1];

size_t serialLength = 0;

bool serialMessageTooLong = false;


// --------------------------------------------------
// Physical output
// --------------------------------------------------

bool isSupportedChannel(int channel) {
  return channel >= 0 && channel < CHANNEL_COUNT;
}


void setChannelIntensity(
  int channel,
  float intensity
) {
  if (!isSupportedChannel(channel)) {
    return;
  }

  intensity = constrain(
    intensity,
    MIN_INTENSITY,
    MAX_INTENSITY
  );

  // Convert OpenSmell normalized intensity
  // 0.0-1.0 to PWM 0-255.
  int pwmValue =
      round(intensity * 255.0);

  analogWrite(
    CHANNEL_PINS[channel],
    pwmValue
  );
}


void setAllChannelsOff() {
  for (
    int channel = 0;
    channel < CHANNEL_COUNT;
    channel++
  ) {
    setChannelIntensity(
      channel,
      0.0
    );
  }
}


void stopRendering() {
  setAllChannelsOff();

  rendering = false;
  renderStartedAt = 0;
  renderDurationMs = 0;
}


// --------------------------------------------------
// OpenSmell responses
// --------------------------------------------------

void sendError(
  const char* code,
  const char* message
) {
  JsonDocument response;

  response["protocol_version"] =
      PROTOCOL_VERSION;

  response["type"] = "error";
  response["code"] = code;
  response["message"] = message;

  serializeJson(
    response,
    Serial
  );

  Serial.println();
}


void sendOk() {
  JsonDocument response;

  response["protocol_version"] =
      PROTOCOL_VERSION;

  response["type"] = "ok";

  serializeJson(
    response,
    Serial
  );

  Serial.println();
}


void sendHello() {
  JsonDocument response;

  response["protocol_version"] =
      PROTOCOL_VERSION;

  response["type"] =
      "hello_response";

  response["device_id"] =
      DEVICE_ID;

  serializeJson(
    response,
    Serial
  );

  Serial.println();
}


void sendCapabilities() {
  JsonDocument response;

  response["protocol_version"] =
      PROTOCOL_VERSION;

  response["type"] =
      "capabilities";

  response["device_id"] =
      DEVICE_ID;

  JsonArray channels =
      response["channels"]
          .to<JsonArray>();

  for (
    int channelNumber = 0;
    channelNumber < CHANNEL_COUNT;
    channelNumber++
  ) {
    JsonObject channel =
        channels.add<JsonObject>();

    channel["channel"] =
        channelNumber;

    channel["min_intensity"] =
        MIN_INTENSITY;

    channel["max_intensity"] =
        MAX_INTENSITY;
  }

  response["min_duration"] =
      MIN_DURATION;

  response["max_duration"] =
      MAX_DURATION;

  serializeJson(
    response,
    Serial
  );

  Serial.println();
}


// --------------------------------------------------
// OpenSmell render handling
// --------------------------------------------------

void handleRender(
  JsonDocument& request
) {

  // ------------------------------
  // Validate duration
  // ------------------------------

  if (
    !request["duration"].is<float>() &&
    !request["duration"].is<int>() &&
    !request["duration"].is<double>()
  ) {
    sendError(
      "invalid_plan",
      "duration must be a number"
    );

    return;
  }

  float duration =
      request["duration"];

  if (
    duration < MIN_DURATION ||
    duration > MAX_DURATION
  ) {
    sendError(
      "invalid_plan",
      "duration outside device capabilities"
    );

    return;
  }


  // ------------------------------
  // Validate commands
  // ------------------------------

  if (
    !request["commands"].is<JsonArray>()
  ) {
    sendError(
      "invalid_plan",
      "commands must be an array"
    );

    return;
  }

  JsonArray commands =
      request["commands"];


  // Start with every channel disabled.
  //
  // This means that channels omitted from the
  // RenderingPlan are explicitly off for this render.
  float targetIntensities[CHANNEL_COUNT];

  for (
    int channel = 0;
    channel < CHANNEL_COUNT;
    channel++
  ) {
    targetIntensities[channel] =
        0.0;
  }


  // Validate the entire plan before touching
  // any physical output.
  for (
    JsonObject command : commands
  ) {

    if (
      !command["channel"].is<int>()
    ) {
      sendError(
        "invalid_plan",
        "channel must be an integer"
      );

      return;
    }

    int channel =
        command["channel"];

    if (
      !isSupportedChannel(channel)
    ) {
      sendError(
        "unsupported_channel",
        "device only supports channels 0, 1, and 2"
      );

      return;
    }


    if (
      !command["intensity"].is<float>() &&
      !command["intensity"].is<int>() &&
      !command["intensity"].is<double>()
    ) {
      sendError(
        "invalid_plan",
        "intensity must be a number"
      );

      return;
    }

    float intensity =
        command["intensity"];

    if (
      intensity < MIN_INTENSITY ||
      intensity > MAX_INTENSITY
    ) {
      sendError(
        "invalid_plan",
        "intensity outside device capabilities"
      );

      return;
    }


    targetIntensities[channel] =
        intensity;
  }


  // ------------------------------
  // Apply validated plan
  // ------------------------------

  for (
    int channel = 0;
    channel < CHANNEL_COUNT;
    channel++
  ) {
    setChannelIntensity(
      channel,
      targetIntensities[channel]
    );
  }


  renderStartedAt =
      millis();

  renderDurationMs =
      (unsigned long)(
        duration * 1000.0
      );

  rendering = true;


  // OpenSmell receives confirmation immediately.
  //
  // The device does not wait for the rendering
  // duration to complete before responding.
  sendOk();
}


// --------------------------------------------------
// Protocol message handling
// --------------------------------------------------

void handleMessage(
  const char* line
) {

  JsonDocument request;

  DeserializationError error =
      deserializeJson(
        request,
        line
      );

  if (error) {
    sendError(
      "invalid_json",
      "unable to parse JSON message"
    );

    return;
  }


  if (
    !request["protocol_version"]
        .is<const char*>()
  ) {
    sendError(
      "invalid_message",
      "protocol_version missing"
    );

    return;
  }


  const char* version =
      request["protocol_version"];

  if (
    strcmp(
      version,
      PROTOCOL_VERSION
    ) != 0
  ) {
    sendError(
      "unsupported_protocol_version",
      "only protocol version 0.1 is supported"
    );

    return;
  }


  if (
    !request["type"]
        .is<const char*>()
  ) {
    sendError(
      "invalid_message",
      "type missing"
    );

    return;
  }


  const char* type =
      request["type"];


  if (
    strcmp(
      type,
      "hello"
    ) == 0
  ) {
    sendHello();
    return;
  }


  if (
    strcmp(
      type,
      "get_capabilities"
    ) == 0
  ) {
    sendCapabilities();
    return;
  }


  if (
    strcmp(
      type,
      "render"
    ) == 0
  ) {
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

  if (
    serialMessageTooLong
  ) {
    sendError(
      "message_too_large",
      "serial message exceeds device limit"
    );

    resetSerialMessage();

    return;
  }


  if (
    serialLength == 0
  ) {
    resetSerialMessage();

    return;
  }


  // Ignore an optional carriage return
  // from CRLF framing.
  if (
    serialLength > 0 &&
    serialBuffer[
      serialLength - 1
    ] == '\r'
  ) {
    serialLength--;
  }


  if (
    serialLength == 0
  ) {
    resetSerialMessage();

    return;
  }


  serialBuffer[
    serialLength
  ] = '\0';

  handleMessage(
    serialBuffer
  );

  resetSerialMessage();
}


void receiveSerialMessages() {

  while (
    Serial.available() > 0
  ) {

    char incoming =
        (char)Serial.read();


    // Newline completes one protocol frame.
    if (
      incoming == '\n'
    ) {
      finishSerialMessage();

      continue;
    }


    // Once the frame is known to be too large,
    // discard bytes until the terminating newline.
    if (
      serialMessageTooLong
    ) {
      continue;
    }


    if (
      serialLength >=
      MAX_SERIAL_MESSAGE_BYTES
    ) {
      serialMessageTooLong = true;

      continue;
    }


    serialBuffer[
      serialLength
    ] = incoming;

    serialLength++;
  }
}


// --------------------------------------------------
// Arduino
// --------------------------------------------------

void setup() {

  for (
    int channel = 0;
    channel < CHANNEL_COUNT;
    channel++
  ) {
    pinMode(
      CHANNEL_PINS[channel],
      OUTPUT
    );
  }


  stopRendering();


  Serial.begin(
    115200
  );


  resetSerialMessage();


  // Do not emit arbitrary text here.
  //
  // SerialDeviceTransport expects protocol
  // responses only.
}


void loop() {

  // Stop rendering automatically without
  // blocking serial communication.
  if (
    rendering
  ) {

    unsigned long elapsed =
        millis() -
        renderStartedAt;

    if (
      elapsed >=
      renderDurationMs
    ) {
      stopRendering();
    }
  }


  // One OpenSmell JSON message per line.
  //
  // Reception is incremental and bounded so a
  // malformed or untrusted peer cannot make the
  // device allocate an arbitrarily large String
  // before a newline is received.
  receiveSerialMessages();
}