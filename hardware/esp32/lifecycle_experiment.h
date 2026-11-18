#pragma once
// Opt-in Draft RFC-0014 implementation experiment. LED outputs only; no odor claim.
#include <cmath>
#include <cstdio>
#include <cstdint>
#ifdef OPENSMELL_NATIVE_BENCH
#include <random>
inline uint32_t lifecycleRandom() { static std::random_device random; return random(); }
#else
#include <esp_system.h>
inline uint32_t lifecycleRandom() { return esp_random(); }
#endif

const char* LIFE_PROFILE = "local-simulator-lifecycle-v1";
const char* LIFE_ERRORS = "local-simulator-errors-v1";
char lifeBoot[33] = {};
char lifeId[80] = {};
const char* lifeState = "none";
uint32_t lifeSequence = 0;
uint32_t lifeStarted = 0;
uint32_t lifeDuration = 0;

bool lifeText(JsonVariantConst value) {
  if (!value.is<const char*>()) return false;
  JsonString text = value.as<JsonString>();
  return text.size() > 0 && text.size() <= 128 && strlen(text.c_str()) == text.size();
}
void writeLife(JsonDocument& reply) { serializeJson(reply, Serial); Serial.println(); }
void lifeError(JsonDocument& request, const char* code, const char* message) {
  JsonDocument reply;
  reply["protocol_version"] = PROTOCOL_VERSION;
  reply["type"] = "error"; reply["code"] = code; reply["message"] = message;
  reply["error_profile"] = LIFE_ERRORS;
  for (const char* field : {"type", "execution_id"}) {
    if (lifeText(request[field])) {
      const char* value = request[field];
      size_t length = strlen(value);
      if (length > 0 && length <= 128)
        reply[strcmp(field, "type") == 0 ? "request_type" : "execution_id"] = value;
    }
  }
  writeLife(reply);
}
void lifeAdvance() {
  if (strcmp(lifeState, "running") == 0 && uint32_t(uint32_t(millis()) - lifeStarted) >= lifeDuration) {
    setAllChannelsOff(); lifeState = "completed";
  }
}
void lifeInitialize() {
  for (int i=0; i<4; ++i) snprintf(lifeBoot+i*8, 9, "%08lx", static_cast<unsigned long>(lifecycleRandom()));
}
bool lifeNumber(JsonVariantConst value) {
  return !value.is<bool>() && (value.is<double>() || value.is<int>()) && std::isfinite(value.as<double>());
}
void lifeObserve() {
  JsonDocument reply;
  reply["profile"] = LIFE_PROFILE; reply["execution_id"] = lifeId; reply["state"] = lifeState;
  writeLife(reply);
}
void handleLifecycleMessage(const char* line) {
  JsonDocument request;
  if (deserializeJson(request, line) || !request.is<JsonObject>()) {
    lifeError(request, "invalid_request", "JSON object required"); return;
  }
  if (!lifeText(request["type"])) {
    lifeError(request, "invalid_request", "Request type required"); return;
  }
  const char* type = request["type"];
  bool render = strcmp(type, "render") == 0;
  if ((render || strcmp(type,"hello")==0 || strcmp(type,"get_capabilities")==0) &&
      (!lifeText(request["protocol_version"]) || strcmp(request["protocol_version"], PROTOCOL_VERSION)!=0)) {
    lifeError(request,"invalid_request","Unsupported protocol"); return;
  }
  if (strcmp(type,"hello")==0) { sendHello(); return; }
  if (strcmp(type,"get_capabilities")==0) { sendCapabilities(); return; }
  if (strcmp(type,"lifecycle_capabilities")==0) {
    JsonDocument reply;
    reply["profile"]=LIFE_PROFILE; reply["status"]=true; reply["stop"]=true; reply["errors"]=LIFE_ERRORS;
    reply["implementation"]="experimental-esp32-led-lifecycle-v1";
    reply["max_message_bytes"]=MAX_SERIAL_MESSAGE_BYTES;
    writeLife(reply); return;
  }
  lifeAdvance();
  if (render) {
    if (strcmp(lifeState,"running")==0) { lifeError(request,"busy","Execution already running"); return; }
    if (!lifeNumber(request["duration"]) || request["duration"].as<double>() < 0.1 || request["duration"].as<double>() > 30.0) {
      lifeError(request,"invalid_request","Invalid duration"); return;
    }
    if (!request["commands"].is<JsonArray>() || request["commands"].size()<1 || request["commands"].size()>CHANNEL_COUNT) {
      lifeError(request,"invalid_request","Require one to three commands"); return;
    }
    float intensities[CHANNEL_COUNT] = {}; bool seen[CHANNEL_COUNT] = {};
    for (JsonVariant command : request["commands"].as<JsonArray>()) {
      if (!command.is<JsonObject>() || command["channel"].is<bool>() || !command["channel"].is<int>()) {
        lifeError(request,"invalid_request","Integer channel required"); return;
      }
      int channel=command["channel"];
      if (!isSupportedChannel(channel) || seen[channel] || !lifeNumber(command["intensity"]) ||
          command["intensity"].as<double>()<MIN_INTENSITY || command["intensity"].as<double>()>MAX_INTENSITY) {
        lifeError(request,"invalid_request","Unsupported/duplicate channel or intensity"); return;
      }
      seen[channel]=true; intensities[channel]=command["intensity"].as<float>();
    }
    if (lifeSequence==UINT32_MAX) { lifeError(request,"invalid_request","Execution identifier space exhausted; explicit reboot required"); return; }
    // Validate completely before touching outputs; generated IDs are fresh per boot/counter.
    ++lifeSequence;
    snprintf(lifeId,sizeof(lifeId),"led-exp-%s-%lu",lifeBoot,static_cast<unsigned long>(lifeSequence));
    lifeStarted=uint32_t(millis()); lifeDuration=uint32_t(std::ceil(request["duration"].as<double>()*1000.0));
    for (int channel=0; channel<CHANNEL_COUNT; ++channel) setChannelIntensity(channel,intensities[channel]);
    lifeState="running";
    JsonDocument reply; reply["protocol_version"]=PROTOCOL_VERSION; reply["type"]="ok"; reply["execution_id"]=lifeId;
    writeLife(reply); return;
  }
  if (strcmp(type,"execution_status")==0 || strcmp(type,"stop")==0) {
    if (!lifeText(request["profile"]) || strcmp(request["profile"],LIFE_PROFILE)!=0) {
      lifeError(request,"unsupported_profile","Unsupported lifecycle profile"); return;
    }
    if (!lifeText(request["execution_id"]) || !lifeId[0] || strcmp(request["execution_id"],lifeId)!=0) {
      lifeError(request,"unknown_execution","Unknown or superseded execution identifier"); return;
    }
    if (strcmp(type,"stop")==0 && strcmp(lifeState,"running")==0) { setAllChannelsOff(); lifeState="stopped"; }
    lifeObserve(); return;
  }
  lifeError(request,"unsupported_request","Unsupported request");
}
