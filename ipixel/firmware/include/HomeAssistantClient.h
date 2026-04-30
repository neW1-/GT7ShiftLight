#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <vector>

struct StoredLightState {
  String entityId;
  String state;
  bool hasBrightness = false;
  int brightness = 0;
  bool hasRgb = false;
  int rgb[3] = {0, 0, 0};
  bool hasColorTemp = false;
  int colorTemp = 0;
};

class HomeAssistantClient {
public:
  void configure(const String &baseUrl, const String &token) {
    _baseUrl = baseUrl;
    _token = token;
    _baseUrl.trim();
    if (_baseUrl.endsWith("/")) {
      _baseUrl.remove(_baseUrl.length() - 1);
    }
  }

  bool ready() const {
    return !_baseUrl.isEmpty() && !_token.isEmpty();
  }

  bool turnOff(const String &entityId) {
    JsonDocument doc;
    doc["entity_id"] = entityId;
    return postService("light", "turn_off", doc);
  }

  bool turnOnRed(const String &entityId, uint8_t brightness) {
    JsonDocument doc;
    doc["entity_id"] = entityId;
    doc["brightness"] = brightness;
    JsonArray rgb = doc["rgb_color"].to<JsonArray>();
    rgb.add(255);
    rgb.add(0);
    rgb.add(0);
    return postService("light", "turn_on", doc);
  }

  bool restoreLight(const StoredLightState &state) {
    JsonDocument doc;
    doc["entity_id"] = state.entityId;
    if (state.state == "off") {
      return postService("light", "turn_off", doc);
    }

    if (state.hasBrightness) {
      doc["brightness"] = state.brightness;
    }
    if (state.hasRgb) {
      JsonArray rgb = doc["rgb_color"].to<JsonArray>();
      rgb.add(state.rgb[0]);
      rgb.add(state.rgb[1]);
      rgb.add(state.rgb[2]);
    } else if (state.hasColorTemp) {
      doc["color_temp"] = state.colorTemp;
    }

    return postService("light", "turn_on", doc);
  }

  bool fetchLightState(const String &entityId, StoredLightState &state) {
    if (!ready()) {
      return false;
    }
    HTTPClient http;
    String url = _baseUrl + "/api/states/" + entityId;
    http.begin(url);
    addAuthHeaders(http);
    int code = http.GET();
    if (code < 200 || code >= 300) {
      Serial.printf("HA state fetch failed for %s: HTTP %d\n", entityId.c_str(), code);
      http.end();
      return false;
    }

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, http.getString());
    http.end();
    if (error) {
      Serial.printf("HA state JSON parse failed for %s\n", entityId.c_str());
      return false;
    }

    state.entityId = entityId;
    state.state = doc["state"] | "off";
    JsonVariant attrs = doc["attributes"];
    if (!attrs.isNull()) {
      if (!attrs["brightness"].isNull()) {
        state.hasBrightness = true;
        state.brightness = attrs["brightness"].as<int>();
      }
      if (!attrs["rgb_color"].isNull() && attrs["rgb_color"].size() >= 3) {
        state.hasRgb = true;
        state.rgb[0] = attrs["rgb_color"][0].as<int>();
        state.rgb[1] = attrs["rgb_color"][1].as<int>();
        state.rgb[2] = attrs["rgb_color"][2].as<int>();
      }
      if (!attrs["color_temp"].isNull()) {
        state.hasColorTemp = true;
        state.colorTemp = attrs["color_temp"].as<int>();
      }
    }
    return true;
  }

private:
  String _baseUrl;
  String _token;

  void addAuthHeaders(HTTPClient &http) {
    http.addHeader("Authorization", "Bearer " + _token);
    http.addHeader("Content-Type", "application/json");
  }

  bool postService(const char *domain, const char *service, JsonDocument &doc) {
    if (!ready()) {
      return false;
    }

    String body;
    serializeJson(doc, body);

    HTTPClient http;
    String url = _baseUrl + "/api/services/" + domain + "/" + service;
    http.begin(url);
    addAuthHeaders(http);
    int code = http.POST(body);
    bool ok = code >= 200 && code < 300;
    if (!ok) {
      Serial.printf("HA service %s/%s failed: HTTP %d\n", domain, service, code);
    }
    http.end();
    return ok;
  }
};

inline std::vector<String> splitCsv(const String &csv) {
  std::vector<String> values;
  int start = 0;
  while (start < (int)csv.length()) {
    int comma = csv.indexOf(',', start);
    if (comma == -1) {
      comma = csv.length();
    }
    String value = csv.substring(start, comma);
    value.trim();
    if (!value.isEmpty()) {
      values.push_back(value);
    }
    start = comma + 1;
  }
  return values;
}

