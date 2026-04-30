# GT7 ESP32 iPixel

Always-on ESP32 firmware for the core Hueflash/Drive experience:

- listens for GT7 telemetry directly from the PS5
- detects active driving versus pause/idle
- controls Home Assistant shift and room lights
- writes current gear and suggested gear to an iPixel-style BLE display
- exposes a small local config web page

This is the embedded replacement path for `hueflash.py` + `drive.py`. The TUI and Stream Deck integrations stay laptop/host tools and are intentionally not part of this firmware.

## Current Status

This folder contains the first Arduino/PlatformIO firmware scaffold. The GT7 telemetry and Home Assistant pieces are implemented around the same protocol details used by `gt-telem`:

- heartbeat `A` to PS5 UDP port `33739`
- telemetry listener on UDP port `33740`
- GT7 Salsa20 key and IV mask
- current gear from the low nibble of `bits`
- suggested gear from the high nibble of `bits`
- rev limit from flag bit 5

The BLE iPixel layer connects by MAC/address and writes to a configurable service/characteristic. The exact iPixel payload format still needs to be confirmed against the real device or the `pypixelcolor` protocol. Until then, the firmware sends a simple template payload such as `G:4|S:2|C:orange`.

## Build

Install PlatformIO, then:

```sh
cd ipixel/firmware
pio run
pio run -t upload
pio device monitor
```

## First Run

If no Wi-Fi credentials are saved, the ESP32 starts a setup access point:

```text
SSID: GT7-iPixel-Setup
URL:  http://192.168.4.1
```

Configure:

- Wi-Fi SSID/password
- PS5 IP
- Home Assistant URL/token
- shift light entity
- comma-separated room light entities
- iPixel BLE address
- iPixel service/characteristic UUIDs

## Next Steps

1. Flash and confirm GT7 telemetry packets decrypt on the ESP32.
2. Use the serial monitor BLE discovery logs to identify the iPixel service and writable characteristic.
3. Capture/confirm the real iPixel BLE payload format.
4. Replace the template text payload in `IpixelDisplay` with the real frame/text protocol.
5. Add OTA updates once the core loop is stable.

