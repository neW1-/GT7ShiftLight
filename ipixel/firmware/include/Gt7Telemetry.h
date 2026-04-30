#pragma once

#include <Arduino.h>
#include <WiFiUdp.h>
#include <Salsa20.h>

struct Gt7Packet {
  bool valid = false;
  float positionX = 0;
  float positionY = 0;
  float positionZ = 0;
  float engineRpm = 0;
  float speedKph = 0;
  int32_t packetId = 0;
  int32_t timeOfDayMs = 0;
  int16_t minAlertRpm = 0;
  int16_t maxAlertRpm = 0;
  int16_t flags = 0;
  uint8_t bits = 0;
  uint8_t throttle = 0;
  uint8_t brake = 0;

  int currentGear() const { return bits & 0x0f; }
  int suggestedGear() const { return (bits >> 4) & 0x0f; }
  bool carsOnTrack() const { return flags & (1 << 0); }
  bool paused() const { return flags & (1 << 1); }
  bool loading() const { return flags & (1 << 2); }
  bool revLimit() const { return flags & (1 << 5); }
};

class Gt7TelemetryClient {
public:
  static constexpr uint16_t ReceivePort = 33739;
  static constexpr uint16_t BindPort = 33740;

  bool begin(const String &ps5Ip) {
    _ps5Ip = ps5Ip;
    if (!_udp.begin(BindPort)) {
      Serial.println("Failed to bind GT7 UDP listener");
      return false;
    }
    _lastHeartbeatMs = 0;
    Serial.printf("GT7 telemetry listening on UDP %u, heartbeat target %s:%u\n",
                  BindPort, _ps5Ip.c_str(), ReceivePort);
    return true;
  }

  void sendHeartbeatIfDue() {
    if (_ps5Ip.isEmpty()) {
      return;
    }
    uint32_t now = millis();
    if (_lastHeartbeatMs != 0 && now - _lastHeartbeatMs < 10000) {
      return;
    }
    _lastHeartbeatMs = now;
    _udp.beginPacket(_ps5Ip.c_str(), ReceivePort);
    _udp.write((const uint8_t *)"A", 1);
    _udp.endPacket();
  }

  bool readPacket(Gt7Packet &packet) {
    int packetSize = _udp.parsePacket();
    if (packetSize <= 0) {
      return false;
    }
    if (packetSize > (int)sizeof(_rxBuffer)) {
      Serial.printf("Dropping oversized GT7 packet: %d bytes\n", packetSize);
      while (_udp.available()) {
        _udp.read();
      }
      return false;
    }

    int read = _udp.read(_rxBuffer, sizeof(_rxBuffer));
    if (read <= 0) {
      return false;
    }

    if (!decrypt(_rxBuffer, read, _plainBuffer)) {
      return false;
    }

    if (read < 4 || memcmp(_plainBuffer, "0S7G", 4) != 0) {
      return false;
    }

    packet = parseTelemetry(_plainBuffer + 4, read - 4);
    packet.valid = true;
    return true;
  }

private:
  String _ps5Ip;
  WiFiUDP _udp;
  uint32_t _lastHeartbeatMs = 0;
  uint8_t _rxBuffer[512];
  uint8_t _plainBuffer[512];

  static uint32_t readU32Le(const uint8_t *buf) {
    return (uint32_t)buf[0] | ((uint32_t)buf[1] << 8) | ((uint32_t)buf[2] << 16) | ((uint32_t)buf[3] << 24);
  }

  static int32_t readI32Le(const uint8_t *buf) {
    return (int32_t)readU32Le(buf);
  }

  static int16_t readI16Le(const uint8_t *buf) {
    return (int16_t)((uint16_t)buf[0] | ((uint16_t)buf[1] << 8));
  }

  static float readFloatLe(const uint8_t *buf) {
    uint32_t raw = readU32Le(buf);
    float value;
    memcpy(&value, &raw, sizeof(value));
    return value;
  }

  static float readFloatAdvance(const uint8_t *buf, size_t &offset) {
    float value = readFloatLe(buf + offset);
    offset += 4;
    return value;
  }

  static int32_t readI32Advance(const uint8_t *buf, size_t &offset) {
    int32_t value = readI32Le(buf + offset);
    offset += 4;
    return value;
  }

  static int16_t readI16Advance(const uint8_t *buf, size_t &offset) {
    int16_t value = readI16Le(buf + offset);
    offset += 2;
    return value;
  }

  bool decrypt(const uint8_t *cipherText, size_t len, uint8_t *plainText) {
    if (len < 0x44) {
      return false;
    }

    static const uint8_t key[32] = {
      'S','i','m','u','l','a','t','o','r',' ','I','n','t','e','r','f',
      'a','c','e',' ','P','a','c','k','e','t',' ','G','T','7',' ','v'
    };
    constexpr uint32_t ivMask = 0xDEADBEAF;

    uint32_t seed = readU32Le(cipherText + 0x40);
    uint32_t iv = seed ^ ivMask;
    uint8_t nonce[8] = {
      (uint8_t)(iv & 0xff),
      (uint8_t)((iv >> 8) & 0xff),
      (uint8_t)((iv >> 16) & 0xff),
      (uint8_t)((iv >> 24) & 0xff),
      (uint8_t)(seed & 0xff),
      (uint8_t)((seed >> 8) & 0xff),
      (uint8_t)((seed >> 16) & 0xff),
      (uint8_t)((seed >> 24) & 0xff),
    };

    Salsa20 salsa;
    salsa.setKey(key, sizeof(key));
    salsa.setIV(nonce, sizeof(nonce));
    salsa.decrypt(plainText, cipherText, len);
    return true;
  }

  Gt7Packet parseTelemetry(const uint8_t *buf, size_t len) {
    Gt7Packet p;
    if (len < 143) {
      return p;
    }

    size_t o = 0;
    p.positionX = readFloatAdvance(buf, o);
    p.positionY = readFloatAdvance(buf, o);
    p.positionZ = readFloatAdvance(buf, o);
    o += 11 * 4; // velocity, rotation, orientation, angular velocity, body height
    p.engineRpm = readFloatAdvance(buf, o);
    o += 3 * 4; // iv, fuel_level, fuel_capacity
    float speedMps = readFloatAdvance(buf, o);
    p.speedKph = speedMps * 3.6f;
    o += 8 * 4; // boost, pressure/temp fields, tire temps
    p.packetId = readI32Advance(buf, o);
    o += 2 * 2; // current_lap, total_laps
    o += 2 * 4; // best_lap_time_ms, last_lap_time_ms
    p.timeOfDayMs = readI32Advance(buf, o);
    o += 2 * 2; // race_start_pos, total_cars
    p.minAlertRpm = readI16Advance(buf, o);
    p.maxAlertRpm = readI16Advance(buf, o);
    o += 2; // calc_max_speed
    p.flags = readI16Advance(buf, o);
    p.bits = buf[o++];
    p.throttle = buf[o++];
    p.brake = buf[o++];
    return p;
  }
};
