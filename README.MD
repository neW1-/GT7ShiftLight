# GT7 Shift Light for Home Assistant

A real-time shift light system for Gran Turismo 7 that controls any Home Assistant light. When you hit the rev limiter in GT7, your light flashes bright red - just like a professional race car!

![GT7 Shift Light Demo](https://img.shields.io/badge/Status-Working-brightgreen)
![Python](https://img.shields.io/badge/Python-3.7+-blue)
![GT7](https://img.shields.io/badge/Gran%20Turismo-7-red)
![Home Assistant](https://img.shields.io/badge/Home-Assistant-blue)

## ✨ Features

- **Real-time telemetry**: Uses GT7's UDP telemetry data at 60Hz
- **GT7 rev limiter detection**: Automatically triggers on GT7's built-in rev limiter
- **Bright red shift light**: Flashes any Home Assistant light bright red when it's time to shift
- **Automatic car detection**: Works with any car's specific rev limit
- **Low CPU usage**: Efficient boolean-based detection
- **Easy setup**: Simple YAML configuration

## 🎯 How It Works

1. **GT7 Telemetry**: Receives real-time telemetry data from Gran Turismo 7 via UDP
2. **Rev Limiter Detection**: Monitors GT7's built-in `rev_limit` flag
3. **Light Control**: Sends commands to your Home Assistant light via REST API
4. **Instant Response**: Light turns red when you hit the rev limiter, off when you shift

## 🛠️ Hardware Requirements

- **PlayStation 5** with Gran Turismo 7
- **Home Assistant** server (Raspberry Pi, NUC, etc.)
- **Any Home Assistant-compatible light** (Hue, LIFX, smart switches, etc.)
- **Network connection** between all devices

## 🏁 Quick Start

### 1. Prerequisites

**Python Dependencies:**
```bash
pip install gt-telem requests pyyaml
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

```yaml
# Home Assistant Configuration
ha_token: "YOUR_LONG_LIVED_ACCESS_TOKEN"
ha_url: "http://YOUR_HA_IP:8123"
hue_light_entity: "light.your_hue_light"

# PlayStation 5 Configuration  
ps5_ip: "YOUR_PS5_IP_ADDRESS"
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

### 4. Run the Shift Light

```bash
python3 hueflash.py
```

You should see:
```
Starting GT7 Hue Shift Light (Rev Limit Mode)
Connected to GT7. Shift light ready!
```

### 5. Test in GT7

1. Start any race or practice session in GT7
2. Rev your engine to the limit
3. Watch your Hue light flash bright red! 🔴

## 📋 Configuration Options

### config.yaml Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `ha_token` | Home Assistant Long-Lived Access Token | `"eyJhbGci..."`  |
| `ha_url` | Home Assistant URL with port | `"http://192.168.1.100:8123"` |
| `hue_light_entity` | Your Hue light's entity ID | `"light.hue_iris_1"` |
| `ps5_ip` | Your PlayStation 5 IP address | `"192.168.1.150"` |

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

To control multiple lights, modify the `hue_light_entity` in config.yaml:
```yaml
hue_light_entity: 
  - "light.hue_iris_1"
  - "light.hue_iris_2" 
  - "light.bedroom_light"
```

Then update the code to handle multiple entities in the API calls.

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
- `rev_limit`: Boolean flag when engine hits rev limiter
- `engine_rpm`: Current engine RPM
- `speed_kph`: Current speed

### Network Protocol

- **GT7 → Script**: UDP telemetry on port 33740
- **Script → Home Assistant**: HTTP REST API calls
- **Home Assistant → Hue**: Zigbee/WiFi commands to Hue Bridge

### Performance

- **CPU Usage**: Minimal (boolean checks only)
- **Network Traffic**: ~60 packets/second from GT7, occasional REST calls to HA
- **Response Time**: Near-instantaneous (< 50ms total latency)

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Mobile app for configuration
- Multiple shift points based on optimal shift RPM
- Integration with other racing games
- Web interface for monitoring

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Acknowledgments

- [gt-telem](https://github.com/RaceCrewAI/gt-telem) - GT7 telemetry library
- [Home Assistant](https://home-assistant.io) - Smart home platform
- [Philips Hue](https://www.philips-hue.com) - Smart lighting system
- Gran Turismo 7 community for telemetry documentation

---

**Ready to race? Fire up GT7 and feel the thrill of a real shift light!** 🏁🔴