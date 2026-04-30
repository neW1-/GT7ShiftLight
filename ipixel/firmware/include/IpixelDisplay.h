#pragma once

#include <Arduino.h>
#include <NimBLEDevice.h>

class IpixelDisplay {
public:
  void configure(bool enabled,
                 const String &address,
                 const String &serviceUuid,
                 const String &characteristicUuid,
                 const String &payloadTemplate,
                 uint8_t brightness,
                 uint32_t refreshMs) {
    _enabled = enabled;
    _address = address;
    _serviceUuid = serviceUuid;
    _characteristicUuid = characteristicUuid;
    _payloadTemplate = payloadTemplate;
    _brightness = brightness;
    _refreshMs = refreshMs;
  }

  void begin() {
    if (!_enabled) {
      return;
    }
    NimBLEDevice::init("GT7-iPixel");
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
  }

  void loop() {
    if (!_enabled || connected() || _address.isEmpty()) {
      return;
    }
    uint32_t now = millis();
    if (now - _lastConnectAttemptMs < 5000) {
      return;
    }
    _lastConnectAttemptMs = now;
    connect();
  }

  bool connected() const {
    return _client && _client->isConnected() && _characteristic;
  }

  void showGear(int currentGear, int suggestedGear, bool revLimit) {
    if (!_enabled) {
      return;
    }
    uint32_t now = millis();
    if (now - _lastWriteMs < _refreshMs) {
      return;
    }
    if (currentGear == _lastGear && suggestedGear == _lastSuggested && revLimit == _lastRevLimit) {
      return;
    }

    loop();
    if (!connected()) {
      return;
    }

    _lastWriteMs = now;
    _lastGear = currentGear;
    _lastSuggested = suggestedGear;
    _lastRevLimit = revLimit;

    String color = "white";
    if (revLimit) {
      color = "red";
    } else if (suggestedGear > 0 && suggestedGear < currentGear) {
      color = "orange";
    } else if (suggestedGear > currentGear) {
      color = "blue";
    } else if (suggestedGear == currentGear && currentGear > 0) {
      color = "green";
    }

    String payload = _payloadTemplate;
    payload.replace("{gear}", formatGear(currentGear));
    payload.replace("{suggested}", formatGear(suggestedGear));
    payload.replace("{color}", color);
    payload.replace("{brightness}", String(_brightness));

    bool ok = _characteristic->writeValue((uint8_t *)payload.c_str(), payload.length(), false);
    if (!ok) {
      Serial.println("iPixel BLE write failed");
    }
  }

private:
  bool _enabled = true;
  String _address;
  String _serviceUuid;
  String _characteristicUuid;
  String _payloadTemplate;
  uint8_t _brightness = 40;
  uint32_t _refreshMs = 100;
  uint32_t _lastConnectAttemptMs = 0;
  uint32_t _lastWriteMs = 0;
  int _lastGear = -999;
  int _lastSuggested = -999;
  bool _lastRevLimit = false;
  NimBLEClient *_client = nullptr;
  NimBLERemoteCharacteristic *_characteristic = nullptr;

  String formatGear(int gear) const {
    if (gear == 0) {
      return "N";
    }
    if (gear < 0 || gear > 8) {
      return "--";
    }
    return String(gear);
  }

  void connect() {
    if (_serviceUuid.isEmpty() || _characteristicUuid.isEmpty()) {
      Serial.println("iPixel UUIDs not configured yet");
      return;
    }

    Serial.printf("Connecting to iPixel BLE device %s\n", _address.c_str());
    NimBLEAddress address(_address.c_str());
    _client = NimBLEDevice::createClient();
    if (!_client->connect(address)) {
      Serial.println("iPixel BLE connection failed");
      NimBLEDevice::deleteClient(_client);
      _client = nullptr;
      return;
    }

    Serial.println("iPixel BLE connected; discovering services");
    for (auto *service : *_client->getServices(true)) {
      Serial.printf("BLE service: %s\n", service->getUUID().toString().c_str());
      for (auto *characteristic : *service->getCharacteristics(true)) {
        Serial.printf("  characteristic: %s props=0x%02x\n",
                      characteristic->getUUID().toString().c_str(),
                      characteristic->getProperties());
      }
    }

    NimBLERemoteService *service = _client->getService(_serviceUuid.c_str());
    if (!service) {
      Serial.println("Configured iPixel service UUID not found");
      _client->disconnect();
      return;
    }

    _characteristic = service->getCharacteristic(_characteristicUuid.c_str());
    if (!_characteristic) {
      Serial.println("Configured iPixel characteristic UUID not found");
      _client->disconnect();
      return;
    }

    Serial.println("iPixel BLE characteristic ready");
  }
};

