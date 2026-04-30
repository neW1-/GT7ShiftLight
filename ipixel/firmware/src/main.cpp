#include <Arduino.h>
#include <ArduinoJson.h>
#include <WebServer.h>
#include <WiFi.h>

#include "AppConfig.h"
#include "Gt7Telemetry.h"
#include "HomeAssistantClient.h"
#include "IpixelDisplay.h"

enum class DriveState {
  Idle,
  Driving,
};

AppConfig config;
WebServer server(80);
Gt7TelemetryClient gt7;
HomeAssistantClient ha;
IpixelDisplay ipixel;
DriveState driveState = DriveState::Idle;
Gt7Packet lastPacket;
uint32_t lastPacketMs = 0;
uint32_t dataFrozenStartMs = 0;
bool telemetryStarted = false;
bool shiftLightActive = false;
std::vector<StoredLightState> savedRoomStates;

const char *SETUP_AP_SSID = "GT7-iPixel-Setup";

String htmlPage() {
  return R"HTML(
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GT7 iPixel Setup</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 760px; margin: 24px auto; padding: 0 16px; background: #111; color: #f4f4f4; }
    label { display: block; margin-top: 14px; font-weight: 700; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 10px; margin-top: 6px; background: #1d1d1d; color: #fff; border: 1px solid #555; border-radius: 6px; }
    button { margin-top: 18px; padding: 10px 14px; border: 0; border-radius: 6px; background: #2e8bff; color: white; font-weight: 700; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 640px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>GT7 iPixel Setup</h1>
  <form id="cfg">
    <div class="row">
      <div><label>Wi-Fi SSID<input name="wifiSsid"></label></div>
      <div><label>Wi-Fi Password<input name="wifiPassword" type="password"></label></div>
    </div>
    <label>PS5 IP<input name="ps5Ip" placeholder="192.168.1.150"></label>
    <label>Home Assistant URL<input name="haUrl" placeholder="http://homeassistant.local:8123"></label>
    <label>Home Assistant Token<textarea name="haToken" rows="3"></textarea></label>
    <label>Shift Light Entity<input name="shiftLightEntity" placeholder="light.hue_iris_1"></label>
    <label>Room Lights, comma-separated<textarea name="roomLightsCsv" rows="2" placeholder="light.living_room, light.office"></textarea></label>
    <div class="row">
      <div><label>Telemetry Timeout (ms)<input name="telemetryTimeoutMs" type="number" min="100"></label></div>
      <div><label>Shift Brightness (0-255)<input name="shiftBrightness" type="number" min="1" max="255"></label></div>
    </div>
    <label>iPixel BLE Address<input name="ipixelAddress" placeholder="aa:bb:cc:dd:ee:ff"></label>
    <label>iPixel Service UUID<input name="ipixelServiceUuid"></label>
    <label>iPixel Characteristic UUID<input name="ipixelCharacteristicUuid"></label>
    <label>iPixel Payload Template<input name="ipixelPayloadTemplate" placeholder="G:{gear}|S:{suggested}|C:{color}"></label>
    <div class="row">
      <div><label>iPixel Brightness (0-100)<input name="ipixelBrightness" type="number" min="0" max="100"></label></div>
      <div><label>Display Refresh (ms)<input name="displayRefreshMs" type="number" min="50"></label></div>
    </div>
    <button type="submit">Save & Reboot</button>
  </form>
  <script>
    async function load() {
      const cfg = await fetch('/api/config').then(r => r.json());
      for (const [key, value] of Object.entries(cfg)) {
        const input = document.querySelector(`[name="${key}"]`);
        if (input) input.value = value ?? '';
      }
    }
    document.getElementById('cfg').addEventListener('submit', async (event) => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.currentTarget).entries());
      for (const key of ['telemetryTimeoutMs', 'shiftBrightness', 'ipixelBrightness', 'displayRefreshMs']) data[key] = Number(data[key]);
      await fetch('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
      document.body.innerHTML = '<h1>Saved</h1><p>The ESP32 is rebooting.</p>';
    });
    load();
  </script>
</body>
</html>
)HTML";
}

void sendConfigJson() {
  JsonDocument doc;
  doc["wifiSsid"] = config.wifiSsid;
  doc["wifiPassword"] = "";
  doc["ps5Ip"] = config.ps5Ip;
  doc["haUrl"] = config.haUrl;
  doc["haToken"] = "";
  doc["shiftLightEntity"] = config.shiftLightEntity;
  doc["roomLightsCsv"] = config.roomLightsCsv;
  doc["telemetryTimeoutMs"] = config.telemetryTimeoutMs;
  doc["shiftBrightness"] = config.shiftBrightness;
  doc["ipixelAddress"] = config.ipixelAddress;
  doc["ipixelServiceUuid"] = config.ipixelServiceUuid;
  doc["ipixelCharacteristicUuid"] = config.ipixelCharacteristicUuid;
  doc["ipixelPayloadTemplate"] = config.ipixelPayloadTemplate;
  doc["ipixelBrightness"] = config.ipixelBrightness;
  doc["displayRefreshMs"] = config.displayRefreshMs;

  String body;
  serializeJson(doc, body);
  server.send(200, "application/json", body);
}

void updateConfigFromJson() {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, server.arg("plain"));
  if (error) {
    server.send(400, "application/json", "{\"error\":\"invalid json\"}");
    return;
  }

  config.wifiSsid = doc["wifiSsid"] | config.wifiSsid;
  String newPassword = doc["wifiPassword"] | "";
  if (!newPassword.isEmpty()) {
    config.wifiPassword = newPassword;
  }
  config.ps5Ip = doc["ps5Ip"] | config.ps5Ip;
  config.haUrl = doc["haUrl"] | config.haUrl;
  String newToken = doc["haToken"] | "";
  if (!newToken.isEmpty()) {
    config.haToken = newToken;
  }
  config.shiftLightEntity = doc["shiftLightEntity"] | config.shiftLightEntity;
  config.roomLightsCsv = doc["roomLightsCsv"] | config.roomLightsCsv;
  config.telemetryTimeoutMs = doc["telemetryTimeoutMs"] | config.telemetryTimeoutMs;
  config.shiftBrightness = doc["shiftBrightness"] | config.shiftBrightness;
  config.ipixelAddress = doc["ipixelAddress"] | config.ipixelAddress;
  config.ipixelServiceUuid = doc["ipixelServiceUuid"] | config.ipixelServiceUuid;
  config.ipixelCharacteristicUuid = doc["ipixelCharacteristicUuid"] | config.ipixelCharacteristicUuid;
  config.ipixelPayloadTemplate = doc["ipixelPayloadTemplate"] | config.ipixelPayloadTemplate;
  config.ipixelBrightness = doc["ipixelBrightness"] | config.ipixelBrightness;
  config.displayRefreshMs = doc["displayRefreshMs"] | config.displayRefreshMs;

  saveConfig(config);
  server.send(200, "application/json", "{\"ok\":true}");
  delay(250);
  ESP.restart();
}

void startWebServer() {
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", htmlPage());
  });
  server.on("/api/config", HTTP_GET, sendConfigJson);
  server.on("/api/config", HTTP_POST, updateConfigFromJson);
  server.begin();
  Serial.println("Config web server started on port 80");
}

void connectWifi() {
  if (config.wifiSsid.isEmpty()) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(SETUP_AP_SSID);
    Serial.printf("Setup AP started: %s at %s\n", SETUP_AP_SSID, WiFi.softAPIP().toString().c_str());
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(config.wifiSsid.c_str(), config.wifiPassword.c_str());
  Serial.printf("Connecting to Wi-Fi SSID %s", config.wifiSsid.c_str());
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi connected: %s\n", WiFi.localIP().toString().c_str());
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(SETUP_AP_SSID);
    Serial.printf("Wi-Fi failed; setup AP started: %s at %s\n", SETUP_AP_SSID, WiFi.softAPIP().toString().c_str());
  }
}

bool packetDataChanged(const Gt7Packet &packet) {
  if (!telemetryStarted) {
    return true;
  }
  if (packet.packetId != lastPacket.packetId || packet.timeOfDayMs != lastPacket.timeOfDayMs) {
    return true;
  }
  if (fabs(packet.engineRpm - lastPacket.engineRpm) > 0.1f || fabs(packet.speedKph - lastPacket.speedKph) > 0.1f) {
    return true;
  }
  if (packet.currentGear() != lastPacket.currentGear() || packet.suggestedGear() != lastPacket.suggestedGear()) {
    return true;
  }
  if (fabs(packet.positionX - lastPacket.positionX) > 0.1f ||
      fabs(packet.positionY - lastPacket.positionY) > 0.1f ||
      fabs(packet.positionZ - lastPacket.positionZ) > 0.1f) {
    return true;
  }
  return false;
}

bool inDrivingContext(const Gt7Packet &packet) {
  return packet.engineRpm > 0 || fabs(packet.speedKph) > 0.1f || packet.currentGear() != 0 || packet.carsOnTrack();
}

void enterDrivingMode() {
  if (driveState == DriveState::Driving) {
    return;
  }
  driveState = DriveState::Driving;
  savedRoomStates.clear();
  Serial.println("Entering GT7 driving mode");

  if (ha.ready()) {
    for (const String &entity : splitCsv(config.roomLightsCsv)) {
      StoredLightState state;
      if (ha.fetchLightState(entity, state)) {
        savedRoomStates.push_back(state);
      }
      ha.turnOff(entity);
    }
  }
}

void exitDrivingMode() {
  if (driveState == DriveState::Idle) {
    return;
  }
  driveState = DriveState::Idle;
  Serial.println("Exiting GT7 driving mode");

  if (shiftLightActive) {
    shiftLightActive = false;
    if (ha.ready() && !config.shiftLightEntity.isEmpty()) {
      ha.turnOff(config.shiftLightEntity);
    }
  }

  if (ha.ready()) {
    for (const StoredLightState &state : savedRoomStates) {
      ha.restoreLight(state);
    }
  }
  savedRoomStates.clear();
}

void handleShiftLight(const Gt7Packet &packet) {
  if (!ha.ready() || config.shiftLightEntity.isEmpty()) {
    return;
  }

  if (packet.revLimit() && !shiftLightActive) {
    shiftLightActive = true;
    ha.turnOnRed(config.shiftLightEntity, config.shiftBrightness);
  } else if (!packet.revLimit() && shiftLightActive) {
    shiftLightActive = false;
    ha.turnOff(config.shiftLightEntity);
  }
}

void handleTelemetryPacket(const Gt7Packet &packet) {
  uint32_t now = millis();
  bool changed = packetDataChanged(packet);
  bool driving = inDrivingContext(packet);

  if (changed) {
    dataFrozenStartMs = 0;
  } else if (dataFrozenStartMs == 0) {
    dataFrozenStartMs = now;
  }

  if (driving && changed && !packet.paused() && !packet.loading()) {
    enterDrivingMode();
    handleShiftLight(packet);
  } else if (driveState == DriveState::Driving) {
    bool timedOut = dataFrozenStartMs != 0 && now - dataFrozenStartMs > config.telemetryTimeoutMs;
    if (!driving || packet.paused() || packet.loading() || timedOut) {
      exitDrivingMode();
    }
  }

  ipixel.showGear(packet.currentGear(), packet.suggestedGear(), packet.revLimit());
  lastPacket = packet;
  telemetryStarted = true;
  lastPacketMs = now;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("GT7 ESP32 iPixel starting");

  loadConfig(config);
  connectWifi();
  startWebServer();

  ha.configure(config.haUrl, config.haToken);
  ipixel.configure(config.ipixelEnabled,
                   config.ipixelAddress,
                   config.ipixelServiceUuid,
                   config.ipixelCharacteristicUuid,
                   config.ipixelPayloadTemplate,
                   config.ipixelBrightness,
                   config.displayRefreshMs);
  ipixel.begin();

  if (WiFi.status() == WL_CONNECTED && !config.ps5Ip.isEmpty()) {
    gt7.begin(config.ps5Ip);
  } else {
    Serial.println("GT7 telemetry is not configured yet");
  }
}

void loop() {
  server.handleClient();
  ipixel.loop();

  if (WiFi.status() != WL_CONNECTED || config.ps5Ip.isEmpty()) {
    delay(10);
    return;
  }

  gt7.sendHeartbeatIfDue();

  Gt7Packet packet;
  if (gt7.readPacket(packet) && packet.valid) {
    handleTelemetryPacket(packet);
  }

  if (driveState == DriveState::Driving && lastPacketMs != 0 && millis() - lastPacketMs > config.telemetryTimeoutMs + 1500) {
    exitDrivingMode();
  }
}

