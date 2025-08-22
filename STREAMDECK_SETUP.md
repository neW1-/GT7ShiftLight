# GT7 Stream Deck Mini Setup Guide

## Stream Deck Mini Integration for GT7

This integration displays GT7 telemetry data on your Stream Deck Mini with real-time updates and all the room lighting automation from the other scripts.

### Stream Deck Button Layout (3x2 grid)
```
# GT7 Stream Deck Mini Integration - Multi-Screen Setup

This guide helps you set up the GT7 Stream Deck Mini integration with multiple screen support for enhanced racing experience.

## 📱 Features

### Main Screen (Default)
- **Button 0 (Shift)**: Red shift light when at rev limit
- **Button 1 (GT7 Suggest)**: GT7's built-in gear suggestions 
- **Button 2 (Gear)**: Current gear display
- **Button 3 (Speed)**: Speed in km/h  
- **Button 4 (RPM)**: RPM with visual gauge
- **Button 5 (Status)**: Racing status (Active/Waiting)

### Gear Screen (Visual)
- **Buttons 0-5 (Gears 1-6)**: Visual gear indicators
  - 🟢 **Bright Green**: Current gear (flashes red at rev limit)
  - 🟠 **Bright Orange**: GT7's suggested gear for next turn
  - ⚫ **Dark/Off**: Other gears
  - **No text** - purely color-based visual feedback

## 🎨 Visual Layout Diagrams

### Main Screen (Default)
```
┌─────────┬─────────┬─────────┐
│ SHIFT   │ GT7     │ GEAR    │
│ Light   │ Suggest │ Current │
│ (Red)   │ (Smart) │ (White) │
├─────────┼─────────┼─────────┤
│ SPEED   │ RPM     │ STATUS  │
│ (km/h)  │ Bar     │ Racing  │
│ (Green) │ (Multi) │ (Yellow)│
└─────────┴─────────┴─────────┘
```

### Gear Screen (Visual Only)
```
┌─────────┬─────────┬─────────┐
│    1    │    2    │    3    │
│  🟢/⚫   │  🟠/⚫   │  ⚫/🟢   │
│         │         │         │
├─────────┼─────────┼─────────┤
│    4    │    5    │    6    │
│  ⚫/🟠   │  ⚫/🟢   │  ⚫/🟠   │
│         │         │         │
└─────────┴─────────┴─────────┘
```

**Color Legend for Gear Screen:**
- 🟢 **Green**: Current gear (bright green, or flashing red at rev limit)
- 🟠 **Orange**: GT7's suggested gear for optimal driving
- ⚫ **Dark**: Inactive gear

### Screen Switching
```
Main Screen ←→ Gear Screen
     ↑              ↓
Press ANY Button to Switch
```
```

### Features
- **Shift Button**: Flashes red when at rev limit (shift light) - Top left
- **GT7 Suggested Gear Button**: Shows GT7's built-in gear recommendations - Top middle  
- **Gear Button**: Shows current gear (R/N/1-8) - Top right
- **Speed Button**: Displays current speed in km/h - Bottom left
- **RPM Button**: Shows current RPM with color-coded progress bar (red when near redline) - Bottom middle
- **Status Button**: Shows driving mode status (Ready/Drive/Active) - Bottom right

### Installation & Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements-streamdeck.txt
   ```

2. **Install macOS HIDAPI Library**
   ```bash
   brew install hidapi
   ```

3. **Stream Deck Setup**
   - Make sure your Stream Deck Mini is connected via USB
   - **Important**: Close the official Stream Deck software before running this script
   - The Stream Deck can only be used by one application at a time

4. **Test Stream Deck Connection**
   ```bash
   python3 test_streamdeck.py
   ```

5. **Run GT7 Stream Deck Integration**
   ```bash
   python3 streamdeck_gt7.py
   ```

6. **Stop the Script**
   - **First try**: Press Ctrl+C
   - **If that doesn't work**: Run `./kill_gt7.sh`
   - **Manual method**: `pkill -f streamdeck_gt7`

### Troubleshooting

#### "No Stream Deck devices found"
- Check USB connection
- Try a different USB port
- Make sure it's a Stream Deck Mini (6 buttons)

#### "Permission denied" or "Could not open HID device"
- **Close Stream Deck software**: The official Stream Deck application locks the device
- **Try with sudo**: `sudo python3 streamdeck_gt7.py` (not recommended for regular use)
- **Check USB permissions**: On some systems, you may need to add udev rules

#### "Stream Deck is in use"
- Close all other applications that might be using the Stream Deck:
  - Official Stream Deck software
  - OBS plugins
  - Other Stream Deck applications

#### Alternative: Console Simulation Mode
If you can't get the Stream Deck working, you can run the simulation mode:
```bash
python3 streamdeck_gt7.py --simulate
```

### Configuration

Uses the same `config.yaml` as the other GT7 scripts:

```yaml
ha_token: "your_home_assistant_token"
hue_light_entity: "light.your_shift_light"
ha_url: "http://your_home_assistant:8123"
ps5_ip: "your_ps5_ip_address"
room_lights:
  - "light.room_light_1"
  - "light.room_light_2"
telemetry_timeout: 5
```

### Real-time Updates
- Stream Deck display updates at 10Hz for smooth visual feedback
- GT7 telemetry updates at 60Hz for responsive shift light
- All room lighting automation features are included

### Visual Examples

**Normal Driving:**
```
[SHIFT ] [ GT7  ] [ GEAR ]
[Ready ] [  5   ] [  5  ]

[SPEED ] [ RPM  ] [STATUS]
[94 kph] [ 3500 ] [Active]
         [▓▓▓░░ ]
```

**Approaching Turn (GT7 suggests lower gear):**
```
[SHIFT ] [ GT7  ] [ GEAR ]
[Ready ] [  3   ] [  5  ]

[SPEED ] [ RPM  ] [STATUS]
[120kph] [ 4200 ] [Active]
         [▓▓▓▓░ ]
```

**GT7 Suggested Gear Colors:**
- 🔵 Blue `5` = GT7 suggests upshift (suggested > current)
- 🟠 Orange `3` = GT7 suggests downshift (suggested < current)  
- 🟢 Green `5` = GT7 agrees with current gear (suggested = current)
- ⚫ Empty (dark gray) = GT7 has no gear suggestion

### Integration with Other Scripts
- **hueflash.py**: Basic shift light (no Stream Deck)
- **drive.py**: Room automation + shift light (no Stream Deck)  
- **drivetui.py**: Full TUI dashboard (terminal-based)
- **streamdeck_gt7.py**: Physical hardware dashboard (Stream Deck Mini)

Choose the version that best fits your setup!
