# GT7 Endurance Racing - Quick Reference 

## 🏁 What's Available for Endurance Racing

Your GT7 telemetry system now has comprehensive endurance racing support! Here's what tire and fuel information is available:

### 🟢 Fuel Data
- **`fuel_level`** - Current fuel in tank (liters/units)  
- **`fuel_capacity`** - Maximum tank capacity
- **Fuel percentage** - Calculated: `(fuel_level / fuel_capacity) * 100`

### 🔥 Tire Temperature Data (Critical for Endurance!)
- **`tire_fl_temp`** - Front-left tire temperature (°C)
- **`tire_fr_temp`** - Front-right tire temperature (°C) 
- **`tire_rl_temp`** - Rear-left tire temperature (°C)
- **`tire_rr_temp`** - Rear-right tire temperature (°C)

**Temperature Guidelines:**
- **Optimal**: 80-100°C (depends on tire compound)
- **Warning**: Above 100°C (increased wear)
- **Critical**: Above 110°C (significant performance loss)
- **Danger**: Above 120°C (severe degradation)

### 🔧 Tire Wear Indicators  
- **`tire_fl_sus_height`** - Front-left suspension height (decreases as tire wears)
- **`tire_fr_sus_height`** - Front-right suspension height
- **`tire_rl_sus_height`** - Rear-left suspension height  
- **`tire_rr_sus_height`** - Rear-right suspension height

### 🌡️ Engine Temperature Monitoring
- **`water_temp`** - Engine coolant temperature (°C)
- **`oil_temp`** - Engine oil temperature (°C)
- **`oil_pressure`** - Engine oil pressure
- **`boost_pressure`** - Turbo boost pressure (kPa)

## 🚀 How to Use It

### Option 1: Endurance TUI (Recommended)
```bash
python3 endurance_tui.py
```
- Complete visual dashboard with fuel, tire temps, engine temps
- Real-time consumption rate calculations
- Pit window alerts
- All room lighting automation included

### Option 2: Add to Existing Scripts
```python
# Add this to your existing drive.py or drivetui.py
from endurance_monitor import EnduranceMonitor, format_endurance_status

endurance_monitor = EnduranceMonitor()

# In your telemetry_callback:
endurance_data = endurance_monitor.update(telemetry)
status_lines = format_endurance_status(endurance_data)
for line in status_lines:
    logger.info(line)
```

### Option 3: Stream Deck Enhancement
Your `streamdeck_gt7.py` already has access to all this data! You could add:
- Fuel level button with percentage
- Tire temperature warning button (changes color when hot)
- Engine temperature status button

## 🎯 Pro Endurance Racing Tips

1. **Monitor tire temps closely** - They're the #1 factor in pace consistency
2. **Track fuel consumption early** - Calculate pit windows in first few laps  
3. **Watch engine temps in traffic** - Drafting increases coolant temperature
4. **Use tire wear data** - Plan optimal tire change timing
5. **Set consumption baselines** - Note fuel usage per lap for strategy

## 📊 Example Endurance Monitoring

```python
def monitor_endurance_status(telemetry):
    # Fuel check
    fuel_pct = (telemetry.fuel_level / telemetry.fuel_capacity) * 100
    
    # Tire temps
    tire_temps = [telemetry.tire_fl_temp, telemetry.tire_fr_temp, 
                  telemetry.tire_rl_temp, telemetry.tire_rr_temp]
    max_temp = max(tire_temps)
    
    # Alerts
    if fuel_pct < 15:
        print("⛽ LOW FUEL - PIT NOW!")
    if max_temp > 110:
        print("🔥 CRITICAL TIRE TEMP - SLOW DOWN!")
    if telemetry.water_temp > 95:
        print("🌡️ ENGINE OVERHEATING!")
```

## 📄 Complete Documentation

- **`ENDURANCE_TELEMETRY.md`** - Complete data reference with all 20+ attributes
- **`endurance_tui.py`** - Ready-to-run endurance racing dashboard  
- **`endurance_monitor.py`** - Modular monitoring to add to existing scripts

Ready to dominate those endurance races! 🏆🏁