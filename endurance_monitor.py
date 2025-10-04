#!/usr/bin/env python3
"""
GT7 Endurance Monitor - Add to existing scripts
==============================================

This module provides endurance racing monitoring functions that can be
integrated into drive.py, drivetui.py, or streamdeck_gt7.py.

Key features:
- Fuel level monitoring with consumption rate calculation
- Tire temperature alerts
- Engine temperature warnings
- Pit window calculations
- Endurance-specific data logging
"""

import time
from datetime import datetime, timedelta

class EnduranceMonitor:
    def __init__(self):
        self.start_time = None
        self.start_fuel = None
        self.fuel_capacity = None
        self.lap_fuel_history = []
        self.tire_temp_history = []
        self.alerts = []
        
    def initialize(self, telemetry):
        """Initialize monitoring with race start data"""
        self.start_time = time.time()
        self.start_fuel = getattr(telemetry, 'fuel_level', 0)
        self.fuel_capacity = getattr(telemetry, 'fuel_capacity', 100)
        print(f"🏁 Endurance monitoring started - Initial fuel: {self.start_fuel:.1f}")
        
    def update(self, telemetry):
        """Update monitoring data and return alerts"""
        if self.start_time is None:
            self.initialize(telemetry)
            
        self.alerts = []
        
        # Fuel monitoring
        fuel_data = self._monitor_fuel(telemetry)
        
        # Tire temperature monitoring  
        tire_data = self._monitor_tires(telemetry)
        
        # Engine temperature monitoring
        engine_data = self._monitor_engine(telemetry)
        
        return {
            'fuel': fuel_data,
            'tires': tire_data, 
            'engine': engine_data,
            'alerts': self.alerts
        }
    
    def _monitor_fuel(self, telemetry):
        """Monitor fuel level and consumption"""
        fuel_level = getattr(telemetry, 'fuel_level', 0)
        fuel_capacity = getattr(telemetry, 'fuel_capacity', self.fuel_capacity or 100)
        
        if fuel_capacity == 0:
            fuel_capacity = 100  # Fallback
            
        fuel_percentage = (fuel_level / fuel_capacity) * 100
        
        # Calculate consumption rate
        elapsed_hours = (time.time() - self.start_time) / 3600 if self.start_time else 0
        fuel_used = self.start_fuel - fuel_level if self.start_fuel else 0
        consumption_rate = fuel_used / elapsed_hours if elapsed_hours > 0 else 0
        
        # Calculate remaining time
        remaining_fuel = fuel_level
        remaining_hours = remaining_fuel / consumption_rate if consumption_rate > 0 else float('inf')
        
        # Fuel alerts
        if fuel_percentage < 10:
            self.alerts.append("⛽ CRITICAL FUEL - PIT NOW!")
        elif fuel_percentage < 20:
            self.alerts.append("⛽ LOW FUEL - Pit soon")
        elif fuel_percentage < 30:
            self.alerts.append("⛽ Plan pit stop")
            
        return {
            'level': fuel_level,
            'percentage': fuel_percentage,
            'consumption_rate': consumption_rate,
            'remaining_hours': remaining_hours,
            'pit_window_open': fuel_percentage < 30
        }
    
    def _monitor_tires(self, telemetry):
        """Monitor tire temperatures"""
        temps = [
            getattr(telemetry, 'tire_fl_temp', 0),
            getattr(telemetry, 'tire_fr_temp', 0),
            getattr(telemetry, 'tire_rl_temp', 0),
            getattr(telemetry, 'tire_rr_temp', 0)
        ]
        
        if all(t == 0 for t in temps):
            return {'temps': temps, 'max': 0, 'avg': 0, 'status': 'No data'}
        
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        # Tire temperature alerts
        if max_temp > 120:
            self.alerts.append("🔥 CRITICAL TIRE TEMP - Slow down!")
            status = 'CRITICAL'
        elif max_temp > 110:
            self.alerts.append("🔥 High tire temps - Easy on throttle")
            status = 'HOT'
        elif max_temp > 100:
            status = 'WARM'
        else:
            status = 'OPTIMAL'
            
        return {
            'temps': temps,
            'max': max_temp,
            'avg': avg_temp,
            'status': status
        }
    
    def _monitor_engine(self, telemetry):
        """Monitor engine temperatures"""
        water_temp = getattr(telemetry, 'water_temp', 0)
        oil_temp = getattr(telemetry, 'oil_temp', 0)
        oil_pressure = getattr(telemetry, 'oil_pressure', 0)
        
        # Engine temperature alerts
        if water_temp > 100:
            self.alerts.append("🌡️ CRITICAL ENGINE TEMP!")
        elif water_temp > 95:
            self.alerts.append("🌡️ High engine temp")
            
        if oil_temp > 130:
            self.alerts.append("🛢️ High oil temp")
            
        return {
            'water_temp': water_temp,
            'oil_temp': oil_temp, 
            'oil_pressure': oil_pressure
        }

def format_endurance_status(data):
    """Format endurance data for display"""
    lines = []
    
    # Fuel status
    fuel = data['fuel']
    if fuel['percentage'] > 0:
        eta = f"{fuel['remaining_hours']:.1f}h" if fuel['remaining_hours'] < 24 else "∞"
        lines.append(f"⛽ Fuel: {fuel['percentage']:.1f}% (Rate: {fuel['consumption_rate']:.1f}/h, ETA: {eta})")
    
    # Tire status  
    tires = data['tires']
    if tires['max'] > 0:
        lines.append(f"🔥 Tires: {tires['avg']:.1f}°C avg, {tires['max']:.1f}°C max ({tires['status']})")
    
    # Engine status
    engine = data['engine']
    if engine['water_temp'] > 0:
        lines.append(f"🌡️ Engine: {engine['water_temp']:.1f}°C water, {engine['oil_temp']:.1f}°C oil")
    
    # Alerts
    if data['alerts']:
        lines.append("🚨 ALERTS: " + " | ".join(data['alerts']))
    
    return lines

# Example integration for your existing scripts:

def add_to_telemetry_callback(telemetry, monitor):
    """
    Example: How to integrate into your existing telemetry_callback functions
    
    Add this to drive.py, drivetui.py, or streamdeck_gt7.py:
    
    # At top of file:
    from endurance_monitor import EnduranceMonitor, format_endurance_status
    endurance_monitor = EnduranceMonitor()
    
    # In your telemetry_callback function:
    endurance_data = endurance_monitor.update(telemetry)
    status_lines = format_endurance_status(endurance_data)
    for line in status_lines:
        logger.info(line)  # or print(line) for console output
    """
    pass

if __name__ == "__main__":
    print("GT7 Endurance Monitor Module")
    print("===========================")
    print("This module is designed to be imported into your existing GT7 scripts.")
    print("See the documentation in ENDURANCE_TELEMETRY.md for usage examples.")