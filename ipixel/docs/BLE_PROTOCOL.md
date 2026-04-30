# iPixel BLE Protocol Notes

The firmware currently has a BLE transport, not a confirmed iPixel renderer.

Why: the existing Python project does not include `pypixelcolor`, and the exact BLE service, characteristic, and payload format need to be verified on your specific display.

## What The Firmware Can Already Do

- Connect to a configured BLE address.
- Discover services and characteristics and print them to serial.
- Write a configurable gear/suggested-gear text payload to the selected characteristic.

## What We Need To Confirm

- iPixel BLE MAC/address.
- Service UUID.
- Writable characteristic UUID.
- Whether writes need response or no-response.
- Payload format for drawing text or frames.

## Discovery Workflow

1. Flash `ipixel/firmware`.
2. Open the serial monitor.
3. Configure the iPixel address in the web UI.
4. Watch the serial output for discovered services/characteristics.
5. Put the writable characteristic UUID into the web UI.

Once the UUIDs are known, the remaining work is replacing the simple template payload with the real iPixel frame/text payload.

