# GT7 Endurance Racing Telemetry Data Reference

Based on the GT7 telemetry system and the `gt-telem` library, here's what tire and fuel information is available for endurance racing:

## 🟢 Fuel Data

| Attribute | Type | Description |
|-----------|------|-------------|
| `fuel_level` | float | Current fuel level (liters/units) |
| `fuel_capacity` | float | Maximum fuel capacity |

**Usage Example:**
```python
fuel_percentage = (telemetry.fuel_level / telemetry.fuel_capacity) * 100
print(f"Fuel: {fuel_percentage:.1f}% ({telemetry.fuel_level:.1f}/{telemetry.fuel_capacity:.1f})")
```

## 🔥 Tire Temperature Data (Critical for Endurance)

| Attribute | Type | Description |
|-----------|------|-------------|
| `tire_fl_temp` | float | Front-left tire temperature (°C) |
| `tire_fr_temp` | float | Front-right tire temperature (°C) |
| `tire_rl_temp` | float | Rear-left tire temperature (°C) |
| `tire_rr_temp` | float | Rear-right tire temperature (°C) |

**Tire Temperature Guidelines:**
- **Optimal**: Usually 80-100°C depending on tire compound
- **Warning**: Above 100°C - tire degradation accelerates
- **Critical**: Above 120°C - significant performance loss

**Usage Example:**
```python
temps = [telemetry.tire_fl_temp, telemetry.tire_fr_temp, 
         telemetry.tire_rl_temp, telemetry.tire_rr_temp]
avg_temp = sum(temps) / len(temps)
hot_tire = max(temps)
print(f"Avg tire temp: {avg_temp:.1f}°C, Hottest: {hot_tire:.1f}°C")
```

## 🔧 Tire Wear Indicators

| Attribute | Type | Description |
|-----------|------|-------------|
| `tire_fl_sus_height` | float | Front-left suspension height (wear indicator) |
| `tire_fr_sus_height` | float | Front-right suspension height (wear indicator) |
| `tire_rl_sus_height` | float | Rear-left suspension height (wear indicator) |
| `tire_rr_sus_height` | float | Rear-right suspension height (wear indicator) |

**Note:** Suspension height decreases as tires wear down. Monitor changes from start values.

## 🏁 Engine Performance (Endurance Critical)

| Attribute | Type | Description |
|-----------|------|-------------|
| `engine_rpm` | float | Current engine RPM |
| `boost_pressure` | float | Turbo boost pressure (kPa) |
| `oil_pressure` | float | Engine oil pressure |
| `water_temp` | float | Engine coolant temperature (°C) |
| `oil_temp` | float | Engine oil temperature (°C) |

**Engine Temperature Guidelines:**
- **Normal Water Temp**: 80-90°C
- **Warning**: Above 95°C
- **Critical**: Above 100°C (engine damage risk)

## 🏆 Race Progress Data

| Attribute | Type | Description |
|-----------|------|-------------|
| `current_lap` | int | Current lap number |
| `total_laps` | int | Total laps in race |
| `best_lap_time` | int | Best lap time (milliseconds) |
| `last_lap_time` | int | Last completed lap time (milliseconds) |
| `race_time` | int | Total race time elapsed |

## 🚩 Status Flags

| Attribute | Type | Description |
|-----------|------|-------------|
| `rev_limit` | bool | True when hitting rev limiter |
| `is_paused` | bool | True when game is paused |
| `hand_brake_active` | bool | True when handbrake is engaged |
| `cars_on_track` | bool | True when other cars are present |

## 📊 Advanced Endurance Monitoring Example

```python
def monitor_endurance_status(telemetry):
    # Fuel monitoring
    fuel_pct = (telemetry.fuel_level / telemetry.fuel_capacity) * 100
    
    # Tire temperature monitoring
    tire_temps = [
        telemetry.tire_fl_temp, telemetry.tire_fr_temp,
        telemetry.tire_rl_temp, telemetry.tire_rr_temp
    ]
    max_temp = max(tire_temps)
    avg_temp = sum(tire_temps) / 4
    
    # Engine monitoring
    water_temp = telemetry.water_temp
    oil_temp = telemetry.oil_temp
    
    # Alerts
    alerts = []
    if fuel_pct < 15:
        alerts.append("⛽ LOW FUEL")
    if max_temp > 110:
        alerts.append("🔥 HOT TIRES")
    if water_temp > 95:
        alerts.append("🌡️ ENGINE HOT")
    
    print(f"Fuel: {fuel_pct:.1f}% | Tire Temp: {avg_temp:.1f}°C | Water: {water_temp:.1f}°C")
    if alerts:
        print("ALERTS: " + " | ".join(alerts))
```

## 🎛️ Extended Data (Heartbeat Type "~")

If you use `TurismoClient(heartbeat_type="~")`, you get additional data:

| Attribute | Type | Description |
|-----------|------|-------------|
| `throttle_filtered` | int | Filtered throttle input |
| `brake_filtered` | int | Filtered brake input |
| `energy_recovery` | float | Hybrid energy recovery value |

## 💡 Endurance Racing Tips

1. **Monitor tire temps closely** - they're the #1 factor in endurance pace
2. **Track fuel consumption rate** - calculate pit windows early
3. **Watch engine temps** - especially in hot weather or drafting
4. **Use tire wear data** - plan tire change timing
5. **Monitor lap times** - degradation affects consistency

## 🔧 Implementation Notes

- Telemetry updates at 60Hz - sample every 60 packets for 1-second intervals
- Store baseline values (fuel capacity, initial suspension heights) at race start
- Calculate rates of change for fuel consumption and tire wear
- Use rolling averages for smooth temperature monitoring
- Implement alerts for critical thresholds

Ready to dominate those endurance races! 🏁