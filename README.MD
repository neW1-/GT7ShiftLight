# GT7 Shift Light & Room Lighting for Home Assistant

A comprehensive lighting system for Gran Turismo 7 that provides multiple ways to experience telemetry data with shift light functionality and immersive room automation.

![GT7 Shift Light Demo](https://img.shields.io/badge/Status-Working-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7+-blue)
![GT7](https://img.shields.io/badge/Gran%20Turismo-7-red)
![Home Assistant](https://img.shields.io/badge/Home-Assistant-blue)

## ✨ Five Different GT7 Experiences

### 📱 Stream Deck Multi-Screen Dashboard (`streamdeck_gt7.py`) 🆕
- **Physical button displays**: Real-time telemetry on Stream Deck Mini hardware (6 buttons, 3x2 layout)
- **Multi-screen layouts**: Two switchable screens - Main telemetry view and Visual gear display
- **Button press switching**: Press ANY button to cycle between screens seamlessly
- **Main screen features**: Shift light, GT7's suggested gear, current gear, speed, RPM with progress bar, driving status
- **Gear screen features**: Visual gear indicators (buttons 1-6) with color coding for current/suggested gears
- **Advanced telemetry**: GT7's built-in gear suggestions displayed in real-time
- **Visual progress indicators**: RPM gauge with color-coded rev limit warnings
- **Brightness control**: Adjustable brightness (1-100%) via command line
- **Complete automation**: Full room lighting and shift light integration
- **Professional hardware setup**: Perfect for dedicated sim racing rigs

### 💻 TUI Racing Dashboard (`drivetui.py`)
- **Real-time visual dashboard**: Terminal-based racing display with progress bars
- **Live telemetry bars**: RPM, Speed, and Fuel level with visual indicators
- **Color-coded status**: Green for normal, red for warnings/critical levels
- **Complete racing info**: Gear, throttle %, brake %, shift light status
- **Room lighting integration**: All the smart lighting features of `drive.py`
- **60Hz updates**: Smooth, responsive real-time data visualization

### 🏠 Immersive Room Lighting (`drive.py`)
- **Automatic room lighting control**: Turns off room lights when driving starts
- **Smart pause detection**: Detects when game is paused (data stops changing) for >1 second
- **Intelligent restoration**: Restores previous room lighting when game is paused/stopped
- **Multiple room support**: Control multiple room lights simultaneously
- **Configurable timeout**: Customizable delay before restoring lights
- **Combined functionality**: Includes shift light + room automation in one script

### 💡 Basic Shift Light (`hueflash.py`)
- **Real-time telemetry**: Uses GT7's UDP telemetry data at 60Hz
- **GT7 rev limiter detection**: Automatically triggers on GT7's built-in rev limiter
- **Bright red shift light**: Flashes any Home Assistant light bright red when it's time to shift
- **Automatic car detection**: Works with any car's specific rev limit
- **Low CPU usage**: Efficient boolean-based detection

## 🎯 How It Works

### Stream Deck Multi-Screen Dashboard (`streamdeck_gt7.py`) 🆕
1. **Physical Hardware Connection**: Connects to Stream Deck Mini (6 buttons in 3x2 layout)
2. **Multi-Screen System**: Two dedicated screen layouts accessible via button press
3. **Main Screen Layout**: [SHIFT][GT7][GEAR] / [SPEED][RPM][STATUS] - Complete telemetry overview
4. **Gear Screen Layout**: [1][2][3] / [4][5][6] - Visual gear indicators with color coding
5. **Real-time Updates**: Updates button displays at 10Hz with live telemetry data
6. **GT7 Integration**: Shows GT7's native suggested gear recommendations
7. **Visual Feedback**: Progress bars, color coding, and flashing indicators
8. **Brightness Control**: Adjustable display brightness (1-100%)
9. **Complete Automation**: All room lighting and shift light features included

### TUI Racing Dashboard (`drivetui.py`)
1. **Terminal Interface**: Creates a professional racing dashboard in your terminal
2. **Real-time Bars**: Live progress bars for RPM (red near redline), Speed, and Fuel
3. **Color Coding**: Green for normal, yellow for warnings, red for critical
4. **Live Updates**: 60Hz telemetry processing with smooth visual feedback
5. **Complete Automation**: All room lighting features integrated

### Basic Shift Light (`hueflash.py`)
1. **GT7 Telemetry**: Receives real-time telemetry data from Gran Turismo 7 via UDP
2. **Rev Limiter Detection**: Monitors GT7's built-in `rev_limit` flag
3. **Light Control**: Sends commands to your Home Assistant light via REST API
4. **Instant Response**: Light turns red when you hit the rev limiter, off when you shift

### Immersive Room Lighting (`drive.py`)
1. **Race Detection**: Monitors telemetry to detect when you're actively driving
2. **Smart Room Control**: Automatically saves current room light states and turns them off
3. **Pause Detection**: Uses advanced data analysis to detect when game is paused (telemetry data stops changing)
4. **Intelligent Restoration**: Waits for configurable timeout (default 0.5s) before restoring lights
5. **Seamless Integration**: Combines shift light functionality with room automation
1. **Real-Time Display**: Curses-based terminal interface with live telemetry visualization
2. **Visual Progress Bars**: RPM, Speed, and Fuel displayed as colored progress bars
3. **Racing Metrics**: Shows gear, throttle %, brake %, and shift light status
4. **Smart Status Display**: Color-coded indicators (green=normal, red=critical)
5. **Complete Integration**: All room lighting features + visual racing dashboard

## 🛠️ Hardware Requirements

- **PlayStation 5** with Gran Turismo 7
- **Home Assistant** server (Raspberry Pi, NUC, etc.)
- **Any Home Assistant-compatible light** (Hue, LIFX, smart switches, etc.)
- **Network connection** between all devices
- **Stream Deck Mini** (optional, for `streamdeck_gt7.py`) - 6 button hardware controller

## 🏁 Quick Start

### 1. Prerequisites

**Python Dependencies:**
```bash
pip install gt-telem requests pyyaml

# For Stream Deck support (optional):
pip install streamdeck pillow
```

**GT7 Setup:**
1. Enable telemetry in GT7: Settings → Network → Enable telemetry

**Home Assistant Setup:**
1. Set up your preferred light integration (Hue, LIFX, etc.)
2. Create a Long-Lived Access Token:
   - Profile → Long-Lived Access Tokens → Create Token
3. Note your light's entity ID (e.g., `light.hue_iris_1`, `light.living_room_lamp`)

### 2. Configuration

Create a `config.yaml` file:

#### Basic Shift Light Configuration:
```yaml
# Home Assistant Configuration
ha_token: "YOUR_LONG_LIVED_ACCESS_TOKEN"
ha_url: "http://YOUR_HA_IP:8123"
hue_light_entity: "light.your_hue_light"

# PlayStation 5 Configuration  
ps5_ip: "YOUR_PS5_IP_ADDRESS"
```

#### Full Room Lighting Configuration: 🆕
```yaml
# Home Assistant Configuration
ha_token: "YOUR_LONG_LIVED_ACCESS_TOKEN"
ha_url: "http://YOUR_HA_IP:8123"

# Shift Light Configuration
hue_light_entity: "light.hue_iris_1"  # Your shift light

# Room Lighting Configuration (NEW)
room_lights:
  - "light.living_room"
  - "light.hallway"
  - "light.office"
  # Add as many room lights as you need

# PlayStation 5 Configuration
ps5_ip: "YOUR_PS5_IP_ADDRESS"

# Telemetry Settings
telemetry_timeout: 0.5  # Seconds to wait before restoring lights when game pauses
```

### 3. Find Your IP Addresses

**Find your PS5 IP:**
- PS5 → Settings → Network → View Connection Status

**Find your Home Assistant IP:**
- Usually shown in the Home Assistant interface
- Or check your router's connected devices

**Find your Hue light entity:**
- Home Assistant → Developer Tools → States
- Search for `light.` entities

### 4. Run the System

#### Basic Shift Light Only:
```bash
python3 hueflash.py
```

#### Full Room Lighting Experience (Recommended): 🆕
```bash
python3 drive.py
```

#### TUI Racing Dashboard Experience (Ultimate): 🆕
```bash
python3 drivetui.py
```

#### Stream Deck Multi-Screen Hardware Experience (Professional): 🆕
```bash
# Default brightness (50%)
python3 streamdeck_gt7.py

# Custom brightness (1-100%)
python3 streamdeck_gt7.py --brightness 75

# Simulation mode (without hardware)
python3 streamdeck_gt7.py --simulate --brightness 25
```

**Stream Deck Features:**
- **Main Screen**: Complete telemetry overview with shift light, GT7 gear suggestions, current gear, speed, RPM progress bar, and status
- **Gear Screen**: Visual gear display (buttons 1-6) with color coding - current gear in green, GT7 suggested gear in orange
- **Screen Switching**: Press ANY button to cycle between Main and Gear screens
- **Brightness Control**: Adjust display brightness from 1-100% via command line
- **Professional Setup**: Perfect for dedicated racing rigs and streaming setups

You should see a real-time racing dashboard:
```
GT7 Drive Mode TUI - Racing Dashboard

Status: DRIVING MODE ACTIVE
Shift Light: Ready

RPM: 5500.0 (68.8%)
[███████████████████████████             ]

Speed (km/h): 125.3 (41.8%)  
[████████████████                        ]

Fuel: 75.0 (75.0%)
[██████████████████████████████          ]

Gear: 4
Throttle: 85.2%
Brake: 0.0%
```

### 5. Test in GT7

1. Start any race or practice session in GT7
2. **With `drive.py`**: Watch your room lights automatically turn off when driving starts! 🌑
3. **With `drivetui.py`**: Experience the full racing dashboard with real-time bars and data! 📊
4. Rev your engine to the limit - watch your shift light flash bright red! 🔴
5. **Pause the game**: Room lights will automatically restore after the timeout period ✨

The TUI dashboard shows:
- **RPM Bar**: Green normally, red when approaching rev limit
- **Speed Bar**: Blue bar showing current speed vs maximum 
- **Fuel Bar**: Green when full, red when low (placeholder for now)
- **Live Stats**: Current gear, throttle %, brake %, shift light status
- **Room Status**: Shows when driving mode is active (lights off)

## 📋 Configuration Options

### config.yaml Settings

| Setting | Description | Example | Used By |
|---------|-------------|---------|---------|
| `ha_token` | Home Assistant Long-Lived Access Token | `"eyJhbGci..."` | All |
| `ha_url` | Home Assistant URL with port | `"http://192.168.1.100:8123"` | All |
| `hue_light_entity` | Your shift light entity ID | `"light.hue_iris_1"` | All |
| `ps5_ip` | Your PlayStation 5 IP address | `"192.168.1.150"` | All |
| `room_lights` | List of room lights to control | `["light.living_room", "light.office"]` | drive.py, drivetui.py |
| `telemetry_timeout` | Seconds before restoring lights when paused | `0.5` | drive.py, drivetui.py |

### Room Lighting Behavior 🆕

When using `drive.py` or `drivetui.py`, the system intelligently manages your room lighting:

1. **Race Start**: Automatically saves current states and turns off all `room_lights`
2. **Active Driving**: Keeps room lights off, shift light active for rev limiter
3. **Game Pause Detection**: Monitors for telemetry data that stops changing
4. **Smart Restoration**: Waits for `telemetry_timeout` seconds, then restores previous room light states
5. **Resume Racing**: If you resume before timeout, lights stay off and timer is cancelled

### TUI Dashboard Controls 🆕

When using `drivetui.py`:
- **q/Q**: Quit the dashboard
- **l/L**: View detailed logs (check `drivetui.log` file)
- **Auto-refresh**: Updates at 60Hz for smooth real-time data
- **Color coding**: Green=normal, Red=warning/critical, Blue=info, Yellow=caution

### Environment Variables (Alternative)

You can also use environment variables instead of config.yaml:

```bash
export HA_TOKEN="your_token_here"
export HA_URL="http://your_ha_ip:8123"  
export HUE_LIGHT_ENTITY="light.your_hue_light"
export PS5_IP="your_ps5_ip"

python3 hueflash.py
```

## 🔧 Troubleshooting

### Common Issues

**"No telemetry data"**
- Check GT7 telemetry is enabled: Settings → Network → Enable telemetry
- Verify PS5 IP address is correct
- Ensure PS5 and computer are on the same network

**"Failed to turn on light"**
- Verify Home Assistant token is valid and not expired
- Check Home Assistant URL and port (usually 8123)
- Confirm Hue light entity ID is correct
- Test Home Assistant API manually:
  ```bash
  curl -H "Authorization: Bearer YOUR_TOKEN" \
       -H "Content-Type: application/json" \
       http://YOUR_HA_IP:8123/api/states/light.your_hue_light
  ```

**"Connection refused"**
- Check all IP addresses are correct
- Verify devices are on the same network
- Restart Home Assistant if needed

**Stream Deck Issues** 🆕
- **"No Stream Deck devices found"**: 
  - Ensure Stream Deck Mini is connected via USB
  - Close the official Stream Deck software (conflicts with direct access)
  - Try running with `sudo` for hardware permissions
  - Use `--simulate` flag to test without hardware
- **"Permission denied accessing Stream Deck"**: 
  - Run with `sudo python3 streamdeck_gt7.py`
  - Or set up proper udev rules for non-root access
  - Use simulation mode: `python3 streamdeck_gt7.py --simulate`
- **Buttons not updating**: Check GT7 telemetry is enabled and PS5 IP is correct

### Debug Mode

Enable debug logging by editing `hueflash.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## 🏎️ Advanced Usage

### Running as a Service

**Linux (systemd):**

Create `/etc/systemd/system/gt7-shift-light.service`:
```ini
[Unit]
Description=GT7 Hue Shift Light
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/gt7-shift-light
ExecStart=/usr/bin/python3 hueflash.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable gt7-shift-light
sudo systemctl start gt7-shift-light
```

### Multiple Lights

#### Shift Light (`hueflash.py`):
To control multiple shift lights, modify the `hue_light_entity` in config.yaml:
```yaml
hue_light_entity: 
  - "light.hue_iris_1"
  - "light.hue_iris_2" 
  - "light.bedroom_light"
```

#### Room Lights (`drive.py`) 🆕:
Room lighting is already designed for multiple lights:
```yaml
room_lights:
  - "light.living_room"
  - "light.kitchen"  
  - "light.hallway"
  - "light.office"
  - "light.bedroom"
```
The system will save individual states and restore each light to its previous setting.

### Custom Timeout

Adjust how quickly room lights restore when game is paused:
```yaml
telemetry_timeout: 1.0   # Wait 1 second (good for frequent pause/resume)
telemetry_timeout: 0.1   # Wait 0.1 seconds (very responsive)  
telemetry_timeout: 5.0   # Wait 5 seconds (less sensitive to brief pauses)
```

### Custom Colors

Change the RGB color in `hueflash.py`:
```python
"rgb_color": [255, 0, 0]    # Red (default)
"rgb_color": [255, 165, 0]  # Orange  
"rgb_color": [255, 255, 0]  # Yellow
"rgb_color": [0, 255, 0]    # Green
```

## 📡 Technical Details

### Telemetry Data

The script uses the `gt-telem` library to receive UDP telemetry from GT7 at 60Hz. Key data points:
- `rev_limit`: Boolean flag when engine hits rev limiter (used by both scripts)
- `engine_rpm`: Current engine RPM (used for race detection)
- `speed_kph`: Current speed (used for race detection)
- `position_x/y/z`: Car position coordinates (used by `drive.py` for pause detection)
- `time_of_day_ms`: Game time (used by `drive.py` for pause detection)

### Advanced Pause Detection (`drive.py`) 🆕

The room lighting system uses sophisticated pause detection:
1. **Data Change Analysis**: Compares current telemetry with previous data
2. **Multi-Point Detection**: Monitors RPM, speed, position, and game time
3. **Freeze Duration Tracking**: Measures how long data has been unchanged  
4. **Smart Timing**: Only triggers room restoration after configured timeout
5. **Resume Detection**: Cancels restoration if driving resumes before timeout

### Network Protocol

- **GT7 → Script**: UDP telemetry on port 33740
- **Script → Home Assistant**: HTTP REST API calls
- **Home Assistant → Lights**: Various protocols (Zigbee, WiFi, Z-Wave) depending on your devices

### Performance

- **CPU Usage**: Minimal (boolean checks and simple data comparison)
- **Network Traffic**: ~60 packets/second from GT7, occasional REST calls to HA
- **Response Time**: Near-instantaneous shift light (< 50ms), smart room lighting (< 1s)
- **Memory Usage**: Low (stores only previous telemetry data for comparison)

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Mobile app for configuration  
- Web interface for monitoring
- Integration with other racing games (F1, Forza, etc.)
- Advanced lighting effects (breathing, pulsing, color transitions)
- Multiple shift points based on optimal shift RPM vs rev limiter
- Voice announcements for race events
- Integration with streaming overlays

## 🎮 Usage Scenarios

### Casual Racing
Use `hueflash.py` for simple shift light functionality without room automation.

### Immersive Racing Setup  
Use `drive.py` for the full experience:
- Lights dim automatically when race starts
- Focus entirely on the track without room light distractions
- Shift light keeps you in the optimal RPM range
- Lights restore automatically when you pause or finish
- Perfect for long racing sessions or competitive events

### Professional Terminal Dashboard
Use `drivetui.py` for the ultimate racing experience:
- Real-time visual dashboard with progress bars for all key metrics
- Color-coded warnings and status indicators
- Professional racing telemetry display
- All immersive lighting features included
- Perfect for streaming, competitive racing, or training sessions
- Monitor performance metrics in real-time

### Professional Hardware Dashboard 🆕
Use `streamdeck_gt7.py` for the ultimate physical racing setup:
- **Multi-screen hardware interface**: Two dedicated screen layouts on physical Stream Deck Mini
- **Main screen telemetry**: Shift light, GT7 gear suggestions, current gear, speed, RPM progress, status
- **Visual gear screen**: Physical buttons 1-6 represent gears with color coding (green=current, orange=suggested)
- **Instant screen switching**: Press any button to cycle between telemetry and gear views
- **Professional presentation**: Perfect for serious sim racing rigs, streaming setups, and competitive racing
- **Customizable brightness**: Adjust display brightness (1-100%) for any lighting condition
- **Complete integration**: All immersive room lighting features included
- **Hardware simulation**: Test functionality without physical hardware using simulation mode

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Acknowledgments

- [gt-telem](https://github.com/RaceCrewAI/gt-telem) - GT7 telemetry library
- [Home Assistant](https://home-assistant.io) - Smart home platform
- [Philips Hue](https://www.philips-hue.com) - Smart lighting system
- Gran Turismo 7 community for telemetry documentation

---

**Ready to race with the ultimate GT7 experience? From simple shift lights to immersive room automation to professional racing dashboards - choose your setup and dominate the track!** 🏁🔴💡📊