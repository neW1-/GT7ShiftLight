#!/usr/bin/env python3
"""
GT7 Endurance Racing Telemetry Inspector
========================================

This script shows all available tire and fuel data for endurance racing in GT7.
Based on the gt-telem library documentation and telemetry model.

Key endurance racing data available:
- Tire temperatures (4 wheels)
- Tire suspension heights 
- Fuel level
- Boost pressure
- Engine temperatures
- Wear indicators
- Performance metrics
"""

import os
import time
from gt_telem.turismo_client import TurismoClient

# Load config
try:
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    PS5_IP = config['ps5_ip']
except:
    PS5_IP = os.getenv('PS5_IP', '192.168.68.145')

def display_endurance_data(telemetry):
    """Display tire and fuel data relevant for endurance racing"""
    
    print("\n" + "="*60)
    print("GT7 ENDURANCE RACING TELEMETRY DATA")
    print("="*60)
    
    # FUEL DATA
    print(f"\n🟢 FUEL STATUS:")
    print(f"   Fuel Level: {getattr(telemetry, 'fuel_level', 'N/A')}")
    print(f"   Fuel Capacity: {getattr(telemetry, 'fuel_capacity', 'N/A')}")
    if hasattr(telemetry, 'fuel_level') and hasattr(telemetry, 'fuel_capacity'):
        fuel_pct = (telemetry.fuel_level / telemetry.fuel_capacity) * 100 if telemetry.fuel_capacity > 0 else 0
        print(f"   Fuel Percentage: {fuel_pct:.1f}%")
    
    # TIRE TEMPERATURES (Critical for endurance racing)
    print(f"\n🔥 TIRE TEMPERATURES:")
    print(f"   Front Left:  {getattr(telemetry, 'tire_fl_temp', 'N/A')}°C")
    print(f"   Front Right: {getattr(telemetry, 'tire_fr_temp', 'N/A')}°C")
    print(f"   Rear Left:   {getattr(telemetry, 'tire_rl_temp', 'N/A')}°C")
    print(f"   Rear Right:  {getattr(telemetry, 'tire_rr_temp', 'N/A')}°C")
    
    # TIRE SUSPENSION HEIGHTS (Tire wear indication)
    print(f"\n🔧 TIRE SUSPENSION HEIGHTS:")
    print(f"   Front Left:  {getattr(telemetry, 'tire_fl_sus_height', 'N/A')}")
    print(f"   Front Right: {getattr(telemetry, 'tire_fr_sus_height', 'N/A')}")
    print(f"   Rear Left:   {getattr(telemetry, 'tire_rl_sus_height', 'N/A')}")
    print(f"   Rear Right:  {getattr(telemetry, 'tire_rr_sus_height', 'N/A')}")
    
    # ENGINE & PERFORMANCE DATA
    print(f"\n🏁 ENGINE & PERFORMANCE:")
    print(f"   Engine RPM: {getattr(telemetry, 'engine_rpm', 'N/A')}")
    print(f"   Boost Pressure: {getattr(telemetry, 'boost_pressure', 'N/A')} kPa")
    print(f"   Oil Pressure: {getattr(telemetry, 'oil_pressure', 'N/A')}")
    print(f"   Water Temperature: {getattr(telemetry, 'water_temp', 'N/A')}°C")
    print(f"   Oil Temperature: {getattr(telemetry, 'oil_temp', 'N/A')}°C")
    
    # RACE STATUS
    print(f"\n🏆 RACE STATUS:")
    print(f"   Current Lap: {getattr(telemetry, 'current_lap', 'N/A')}")
    print(f"   Total Laps: {getattr(telemetry, 'total_laps', 'N/A')}")
    print(f"   Best Lap Time: {getattr(telemetry, 'best_lap_time', 'N/A')}")
    print(f"   Last Lap Time: {getattr(telemetry, 'last_lap_time', 'N/A')}")
    
    # ADDITIONAL ENDURANCE-RELEVANT DATA
    print(f"\n⚙️  ADDITIONAL DATA:")
    print(f"   Speed: {getattr(telemetry, 'speed_kph', 'N/A')} km/h")
    print(f"   Current Gear: {getattr(telemetry, 'current_gear', 'N/A')}")
    print(f"   Suggested Gear: {getattr(telemetry, 'suggested_gear', 'N/A')}")
    print(f"   Throttle: {getattr(telemetry, 'throttle', 'N/A')}")
    print(f"   Brake: {getattr(telemetry, 'brake', 'N/A')}")
    
    # FLAGS & INDICATORS
    print(f"\n🚩 FLAGS & INDICATORS:")
    print(f"   Rev Limit: {getattr(telemetry, 'rev_limit', 'N/A')}")
    print(f"   Is Paused: {getattr(telemetry, 'is_paused', 'N/A')}")
    print(f"   Hand Brake: {getattr(telemetry, 'hand_brake_active', 'N/A')}")
    
    print("="*60)
    print("Press Ctrl+C to stop monitoring...")

def main():
    print("GT7 Endurance Racing Telemetry Monitor")
    print("=====================================")
    print(f"Connecting to GT7 at {PS5_IP}...")
    print("\nMake sure you're in an active race or practice session!")
    print("This will show tire temperatures, fuel level, and other endurance data.")
    
    packet_count = 0
    
    def telemetry_callback(telemetry):
        nonlocal packet_count
        packet_count += 1
        
        # Show data every 60 packets (about once per second at 60Hz)
        if packet_count % 60 == 0:
            display_endurance_data(telemetry)
    
    try:
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        client.start()
        
        print("✅ Connected! Monitoring endurance racing data...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitor...")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure GT7 is running")
        print("2. Check telemetry is enabled in GT7 Settings → Network")
        print("3. Verify PS5 IP address in config.yaml")
        print("4. Ensure you're in an active race (not menus)")
    finally:
        if 'client' in locals():
            client.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()