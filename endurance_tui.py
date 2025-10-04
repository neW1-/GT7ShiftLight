#!/usr/bin/env python3
"""
GT7 Endurance TUI - Enhanced for Long Racing
============================================

Enhanced version of drivetui.py specifically designed for endurance racing with:
- Real-time fuel monitoring with consumption rate calculation
- Tire temperature monitoring with alerts
- Engine temperature warnings  
- Pit window calculations
- Endurance-specific data logging
- All the room lighting automation from drive.py

This is perfect for:
- Endurance races
- Long practice sessions
- Fuel and tire strategy planning
- Temperature management

Usage:
    python3 endurance_tui.py

Controls:
    q/Q - Quit
    r/R - Reset endurance monitoring
    l/L - View logs
"""

import os
import time
import requests
import logging
import curses
import threading
import signal
import sys
from gt_telem.turismo_client import TurismoClient
from threading import Timer
from endurance_monitor import EnduranceMonitor, format_endurance_status

# Load configuration  
try:
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    PS5_IP = config['ps5_ip']
    HA_URL = config['home_assistant']['url'] 
    HA_TOKEN = config['home_assistant']['token']
    HUE_LIGHT_ENTITY = config['hue_light_entity']
    ROOM_LIGHTS = config.get('room_lights', [])
    TELEMETRY_TIMEOUT = config.get('telemetry_timeout', 0.5)
except Exception as e:
    print(f"Error loading config: {e}")
    print("Using environment variables...")
    PS5_IP = os.getenv('PS5_IP', '192.168.68.145')
    HA_URL = os.getenv('HA_URL')
    HA_TOKEN = os.getenv('HA_TOKEN') 
    HUE_LIGHT_ENTITY = os.getenv('HUE_LIGHT_ENTITY')
    ROOM_LIGHTS = []
    TELEMETRY_TIMEOUT = 0.5

# Global state
current_telemetry = None
driving_mode_active = False
shift_light_active = False
last_telemetry_data = None
data_frozen_start = None
telemetry_timer = None
room_lights_saved = False
saved_room_states = {}
tui_active = False
endurance_monitor = EnduranceMonitor()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('endurance_tui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def call_ha_api(endpoint, method='POST', data=None):
    """Call Home Assistant API"""
    if not HA_URL or not HA_TOKEN:
        return False
        
    try:
        headers = {
            'Authorization': f'Bearer {HA_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        url = f"{HA_URL}/api/{endpoint}"
        
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=5)
            
        return response.status_code < 400
        
    except Exception as e:
        logger.error(f"HA API call failed: {e}")
        return False

def set_shift_light_brightness(brightness):
    """Set shift light brightness (0.0 to 1.0)"""
    if not HUE_LIGHT_ENTITY:
        return
        
    brightness_value = max(0, min(255, int(brightness * 255)))
    
    data = {
        'entity_id': HUE_LIGHT_ENTITY,
    }
    
    if brightness > 0:
        data.update({
            'brightness': brightness_value,
            'rgb_color': [255, 0, 0]  # Red for shift light
        })
        call_ha_api('services/light/turn_on', data=data)
    else:
        call_ha_api('services/light/turn_off', data=data)

def save_room_light_states():
    """Save current room light states"""
    global saved_room_states, room_lights_saved
    
    if not ROOM_LIGHTS or room_lights_saved:
        return True
        
    logger.info("Saving room light states...")
    saved_room_states = {}
    
    for light_entity in ROOM_LIGHTS:
        try:
            # Get current state
            if call_ha_api(f'states/{light_entity}', method='GET'):
                saved_room_states[light_entity] = True  # Simplified for now
                
        except Exception as e:
            logger.error(f"Failed to save state for {light_entity}: {e}")
    
    room_lights_saved = True
    return True

def turn_off_room_lights():
    """Turn off all room lights"""
    if not ROOM_LIGHTS:
        return
        
    for light_entity in ROOM_LIGHTS:
        call_ha_api('services/light/turn_off', data={'entity_id': light_entity})

def restore_room_lights():
    """Restore room lights to saved states"""
    global room_lights_saved, saved_room_states
    
    if not ROOM_LIGHTS or not room_lights_saved:
        return
        
    logger.info("Restoring room lights...")
    
    for light_entity in ROOM_LIGHTS:
        if light_entity in saved_room_states:
            call_ha_api('services/light/turn_on', data={'entity_id': light_entity})
    
    room_lights_saved = False
    saved_room_states = {}

def enter_driving_mode():
    """Enter driving mode - save and turn off room lights"""
    global driving_mode_active
    
    if driving_mode_active:
        return
        
    driving_mode_active = True
    logger.info("🏁 Entering driving mode")
    
    if save_room_light_states():
        turn_off_room_lights()
        logger.info("💡 Room lights OFF for immersion")

def exit_driving_mode():
    """Exit driving mode - restore room lights"""
    global driving_mode_active, shift_light_active
    
    if not driving_mode_active:
        return
        
    driving_mode_active = False
    shift_light_active = False
    
    logger.info("🏁 Exiting driving mode")
    restore_room_lights()
    set_shift_light_brightness(0.0)
    logger.info("💡 Room lights restored")

class EnduranceTUI:
    def __init__(self):
        self.stdscr = None
        self.height = 0
        self.width = 0
        self.running = True
        
    def setup_colors(self):
        """Setup color pairs for the TUI"""
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)      # Red (critical)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)    # Green (good)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # Yellow (warning)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)     # Cyan (info)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # Magenta (special)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)    # White (title)
        curses.init_pair(7, curses.COLOR_RED, curses.COLOR_WHITE)      # Red on white (alert)

    def draw_bar(self, y, x, width, value, max_value, label, color, show_percentage=True):
        """Draw a progress bar"""
        if max_value <= 0:
            max_value = 1
            
        percentage = min(100, (value / max_value) * 100)
        filled_width = int((percentage / 100) * width)
        
        # Draw label
        self.stdscr.addstr(y, x, f"{label}:", color)
        
        # Draw bar
        bar_y = y + 1
        bar = "█" * filled_width + "░" * (width - filled_width)
        self.stdscr.addstr(bar_y, x, bar, color)
        
        # Draw value
        if show_percentage:
            value_text = f"{percentage:.1f}% ({value:.1f}/{max_value:.1f})"
        else:
            value_text = f"{value:.1f}"
        self.stdscr.addstr(bar_y, x + width + 2, value_text, color)

    def draw_status_line(self, y, x, text, color):
        """Draw a status line"""
        if y < self.height - 1 and x + len(text) < self.width:
            self.stdscr.addstr(y, x, text, color)

    def refresh_display(self):
        """Update the display with current telemetry data"""
        global current_telemetry, driving_mode_active, shift_light_active
        
        self.stdscr.clear()
        
        # Title
        title = "GT7 ENDURANCE RACING TUI - Long Distance Dashboard"
        self.stdscr.addstr(0, max(0, (self.width - len(title)) // 2), title, curses.color_pair(6) | curses.A_BOLD)
        
        if current_telemetry is None:
            self.stdscr.addstr(2, 2, "Waiting for GT7 telemetry data...", curses.color_pair(3))
            self.stdscr.addstr(4, 2, "Make sure GT7 is running and telemetry is enabled.", curses.color_pair(3))
            self.stdscr.addstr(5, 2, "Settings → Network → Enable Telemetry", curses.color_pair(3))
            self.stdscr.refresh()
            return
        
        y = 2
        
        # Connection status
        status_color = curses.color_pair(2) if driving_mode_active else curses.color_pair(3)
        status_text = "ENDURANCE MODE ACTIVE" if driving_mode_active else "Connected - Waiting for race"
        self.draw_status_line(y, 2, f"Status: {status_text}", status_color)
        y += 1
        
        # Shift light indicator
        if shift_light_active:
            shift_text = "🔴 SHIFT NOW! 🔴"
            shift_color = curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK
        else:
            shift_text = "Shift Light: Ready"
            shift_color = curses.color_pair(4)
        self.draw_status_line(y, 2, shift_text, shift_color)
        y += 2
        
        # Get telemetry values
        rpm = getattr(current_telemetry, 'engine_rpm', 0)
        speed = getattr(current_telemetry, 'speed_kph', 0)
        gear = getattr(current_telemetry, 'current_gear', 0)
        throttle = getattr(current_telemetry, 'throttle', 0)
        brake = getattr(current_telemetry, 'brake', 0)
        
        # Get endurance data
        endurance_data = endurance_monitor.update(current_telemetry)
        
        # Basic telemetry bars
        max_rpm = 8000
        max_speed = 300
        
        # RPM Bar
        rpm_color = curses.color_pair(1) if rpm > max_rpm * 0.9 else curses.color_pair(2)
        self.draw_bar(y, 2, 40, rpm, max_rpm, "RPM", rpm_color, False)
        y += 3
        
        # Speed Bar  
        speed_color = curses.color_pair(4)
        self.draw_bar(y, 2, 40, speed, max_speed, "Speed (km/h)", speed_color, False)
        y += 3
        
        # ENDURANCE DATA SECTION
        self.draw_status_line(y, 2, "=== ENDURANCE RACING DATA ===", curses.color_pair(6) | curses.A_BOLD)
        y += 2
        
        # Fuel Bar
        fuel = endurance_data['fuel']
        if fuel['percentage'] > 0:
            fuel_color = curses.color_pair(1) if fuel['percentage'] < 15 else curses.color_pair(3) if fuel['percentage'] < 30 else curses.color_pair(2)
            self.draw_bar(y, 2, 40, fuel['percentage'], 100, "Fuel", fuel_color)
            y += 3
            
            # Fuel consumption info
            if fuel['consumption_rate'] > 0:
                eta_text = f"{fuel['remaining_hours']:.1f}h" if fuel['remaining_hours'] < 24 else "∞"
                fuel_info = f"Consumption: {fuel['consumption_rate']:.1f}/h | Remaining: {eta_text}"
                self.draw_status_line(y, 2, fuel_info, curses.color_pair(4))
                y += 1
        
        # Tire temperatures
        tires = endurance_data['tires']
        if tires['max'] > 0:
            y += 1
            self.draw_status_line(y, 2, "Tire Temperatures:", curses.color_pair(6))
            y += 1
            
            temp_labels = ["FL", "FR", "RL", "RR"]
            for i, (label, temp) in enumerate(zip(temp_labels, tires['temps'])):
                temp_color = curses.color_pair(1) if temp > 110 else curses.color_pair(3) if temp > 100 else curses.color_pair(2)
                temp_text = f"{label}: {temp:.1f}°C"
                self.draw_status_line(y, 2 + i * 15, temp_text, temp_color)
            y += 2
            
            # Temperature summary
            temp_summary = f"Avg: {tires['avg']:.1f}°C | Max: {tires['max']:.1f}°C | Status: {tires['status']}"
            temp_color = curses.color_pair(1) if tires['status'] == 'CRITICAL' else curses.color_pair(3) if tires['status'] == 'HOT' else curses.color_pair(2)
            self.draw_status_line(y, 2, temp_summary, temp_color)
            y += 1
        
        # Engine temperatures
        engine = endurance_data['engine']
        if engine['water_temp'] > 0:
            y += 1
            engine_color = curses.color_pair(1) if engine['water_temp'] > 95 else curses.color_pair(3) if engine['water_temp'] > 90 else curses.color_pair(2)
            engine_text = f"Engine: Water {engine['water_temp']:.1f}°C | Oil {engine['oil_temp']:.1f}°C"
            self.draw_status_line(y, 2, engine_text, engine_color)
            y += 1
        
        # Current driving stats
        y += 1
        self.draw_status_line(y, 2, "=== CURRENT STATUS ===", curses.color_pair(6))
        y += 1
        
        stats_text = f"Gear: {gear} | Throttle: {throttle:.0f}% | Brake: {brake:.0f}%"
        self.draw_status_line(y, 2, stats_text, curses.color_pair(4))
        y += 1
        
        # Alerts section
        alerts = endurance_data['alerts']
        if alerts:
            y += 1
            self.draw_status_line(y, 2, "🚨 ALERTS:", curses.color_pair(1) | curses.A_BOLD)
            y += 1
            for alert in alerts:
                self.draw_status_line(y, 4, alert, curses.color_pair(1) | curses.A_BLINK)
                y += 1
        
        # Controls
        y = self.height - 3
        controls = "Controls: Q=Quit | R=Reset monitoring | L=View logs"
        self.draw_status_line(y, 2, controls, curses.color_pair(6))
        
        self.stdscr.refresh()

    def handle_input(self):
        """Handle keyboard input"""
        global endurance_monitor
        
        self.stdscr.nodelay(True)  # Non-blocking input
        
        try:
            key = self.stdscr.getch()
            if key != -1:  # Key was pressed
                if key in [ord('q'), ord('Q')]:
                    self.running = False
                elif key in [ord('r'), ord('R')]:
                    # Reset endurance monitoring
                    endurance_monitor = EnduranceMonitor()
                    logger.info("🔄 Endurance monitoring reset")
                elif key in [ord('l'), ord('L')]:
                    # Open log file (basic implementation)
                    logger.info("📄 Check endurance_tui.log for detailed logs")
                    
        except curses.error:
            pass  # No input available

    def run(self, stdscr):
        """Main TUI loop"""
        global tui_active
        
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Setup
        curses.curs_set(0)  # Hide cursor
        self.setup_colors()
        tui_active = True
        
        logger.info("🖥️ Endurance TUI started")
        
        try:
            while self.running:
                self.refresh_display()
                self.handle_input()
                time.sleep(0.1)  # 10 FPS refresh rate
                
        except KeyboardInterrupt:
            pass
        finally:
            tui_active = False
            logger.info("🖥️ Endurance TUI stopped")

def is_telemetry_data_changing(packet):
    """Check if telemetry data is actually changing"""
    global last_telemetry_data, data_frozen_start
    
    try:
        current_data = (
            getattr(packet, 'engine_rpm', 0),
            getattr(packet, 'speed_kph', 0),
            getattr(packet, 'current_gear', 0),
            getattr(packet, 'throttle', 0),
            getattr(packet, 'brake', 0)
        )
        
        if last_telemetry_data != current_data:
            last_telemetry_data = current_data
            data_frozen_start = None
            return True, 0
        else:
            if data_frozen_start is None:
                data_frozen_start = time.time()
            
            frozen_duration = time.time() - data_frozen_start
            return False, frozen_duration
            
    except Exception as e:
        logger.error(f"Error checking telemetry data: {e}")
        return True, 0

def is_actually_driving(packet):
    """Check if we're in a driving context"""
    try:
        rpm = getattr(packet, 'engine_rpm', 0)
        speed = getattr(packet, 'speed_kph', 0)
        gear = getattr(packet, 'current_gear', 0)
        
        return rpm > 0 or abs(speed) > 0.1 or gear != 0
        
    except Exception as e:
        logger.error(f"Error checking driving context: {e}")
        return False

def delayed_exit_driving_mode():
    """Exit driving mode after delay"""
    time.sleep(TELEMETRY_TIMEOUT)
    exit_driving_mode()

def telemetry_callback(telemetry):
    """Enhanced telemetry callback with endurance monitoring"""
    global current_telemetry, shift_light_active, telemetry_timer
    
    current_telemetry = telemetry
    
    # Check driving context and data changes
    in_race_context = is_actually_driving(telemetry)
    data_changing, frozen_duration = is_telemetry_data_changing(telemetry)
    
    if in_race_context:
        if data_changing:
            # Cancel any pending exit timer
            if telemetry_timer:
                telemetry_timer.cancel()
                telemetry_timer = None
            
            # Enter driving mode
            enter_driving_mode()
            
            # Handle shift light
            at_rev_limit = getattr(telemetry, 'rev_limit', False)
            
            if at_rev_limit and not shift_light_active:
                logger.info("🔴 Shift light ON - Rev limit reached!")
                shift_light_active = True
                set_shift_light_brightness(1.0)
                
            elif not at_rev_limit and shift_light_active:
                logger.info("⚫ Shift light OFF - Rev limit cleared")
                shift_light_active = False
                set_shift_light_brightness(0.0)
        else:
            # Data frozen in driving context - start exit timer
            if frozen_duration > 1.0 and not telemetry_timer:
                logger.info(f"⏸️ Data frozen for {frozen_duration:.1f}s - Starting exit timer")
                telemetry_timer = Timer(TELEMETRY_TIMEOUT, delayed_exit_driving_mode)
                telemetry_timer.start()
    else:
        # Not in racing context - exit driving mode
        if data_changing or frozen_duration > 30.0:
            exit_driving_mode()

def main():
    logger.info("Starting GT7 Endurance TUI with Room Lighting")
    logger.info(f"Configured room lights: {ROOM_LIGHTS}")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    logger.info(f"Telemetry timeout: {TELEMETRY_TIMEOUT} seconds")
    
    tui = EnduranceTUI()
    
    def signal_handler(signum, frame):
        """Handle Ctrl+C gracefully"""
        tui.running = False
        exit_driving_mode()
        logger.info("Shutdown signal received")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start telemetry client
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        client.start()
        
        logger.info("Connected to GT7. Starting endurance TUI...")
        
        # Run TUI
        curses.wrapper(tui.run)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Clean shutdown
        global telemetry_timer
        if telemetry_timer:
            telemetry_timer.cancel()
        
        exit_driving_mode()
        
        if 'client' in locals():
            client.stop()
        
        logger.info("Endurance TUI shutdown complete!")

if __name__ == "__main__":
    main()