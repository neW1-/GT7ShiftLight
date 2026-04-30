#pragma once

#include <Arduino.h>
#include <Preferences.h>

struct AppConfig {
  String wifiSsid;
  String wifiPassword;
  String ps5Ip;
  String haUrl;
  String haToken;
  String shiftLightEntity;
  String roomLightsCsv;
  uint32_t telemetryTimeoutMs = 1000;
  uint8_t shiftBrightness = 255;
  bool ipixelEnabled = true;
  String ipixelAddress;
  String ipixelServiceUuid;
  String ipixelCharacteristicUuid;
  String ipixelPayloadTemplate = "G:{gear}|S:{suggested}|C:{color}";
  uint8_t ipixelBrightness = 40;
  uint32_t displayRefreshMs = 100;
};

inline String prefGetString(Preferences &prefs, const char *key, const String &fallback = "") {
  return prefs.getString(key, fallback);
}

inline void loadConfig(AppConfig &cfg) {
  Preferences prefs;
  prefs.begin("gt7ipixel", true);
  cfg.wifiSsid = prefGetString(prefs, "wifiSsid");
  cfg.wifiPassword = prefGetString(prefs, "wifiPass");
  cfg.ps5Ip = prefGetString(prefs, "ps5Ip");
  cfg.haUrl = prefGetString(prefs, "haUrl");
  cfg.haToken = prefGetString(prefs, "haToken");
  cfg.shiftLightEntity = prefGetString(prefs, "shiftEntity");
  cfg.roomLightsCsv = prefGetString(prefs, "roomLights");
  cfg.telemetryTimeoutMs = prefs.getUInt("telemTimeout", cfg.telemetryTimeoutMs);
  cfg.shiftBrightness = prefs.getUChar("shiftBright", cfg.shiftBrightness);
  cfg.ipixelEnabled = prefs.getBool("ipixelOn", cfg.ipixelEnabled);
  cfg.ipixelAddress = prefGetString(prefs, "ipixAddr");
  cfg.ipixelServiceUuid = prefGetString(prefs, "ipixSvc");
  cfg.ipixelCharacteristicUuid = prefGetString(prefs, "ipixChr");
  cfg.ipixelPayloadTemplate = prefGetString(prefs, "ipixTpl", cfg.ipixelPayloadTemplate);
  cfg.ipixelBrightness = prefs.getUChar("ipixBright", cfg.ipixelBrightness);
  cfg.displayRefreshMs = prefs.getUInt("displayMs", cfg.displayRefreshMs);
  prefs.end();
}

inline void saveConfig(const AppConfig &cfg) {
  Preferences prefs;
  prefs.begin("gt7ipixel", false);
  prefs.putString("wifiSsid", cfg.wifiSsid);
  prefs.putString("wifiPass", cfg.wifiPassword);
  prefs.putString("ps5Ip", cfg.ps5Ip);
  prefs.putString("haUrl", cfg.haUrl);
  prefs.putString("haToken", cfg.haToken);
  prefs.putString("shiftEntity", cfg.shiftLightEntity);
  prefs.putString("roomLights", cfg.roomLightsCsv);
  prefs.putUInt("telemTimeout", cfg.telemetryTimeoutMs);
  prefs.putUChar("shiftBright", cfg.shiftBrightness);
  prefs.putBool("ipixelOn", cfg.ipixelEnabled);
  prefs.putString("ipixAddr", cfg.ipixelAddress);
  prefs.putString("ipixSvc", cfg.ipixelServiceUuid);
  prefs.putString("ipixChr", cfg.ipixelCharacteristicUuid);
  prefs.putString("ipixTpl", cfg.ipixelPayloadTemplate);
  prefs.putUChar("ipixBright", cfg.ipixelBrightness);
  prefs.putUInt("displayMs", cfg.displayRefreshMs);
  prefs.end();
}

