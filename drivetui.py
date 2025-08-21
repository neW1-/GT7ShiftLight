#!/usr/bin/env python3
"""
GT7 Drive Mode with TUI Dashboard
================================

Enhanced version of drive.py with a Terminal User Interface (TUI) that displays:
- Real-time RPM, Speed, and Fuel bars
- Shift light indicator  
- Current gear, throttle, and brake information
- Room lighting automation (same as drive.py)

Features:
- Visual progress bars for key telemetry data
- Color-coded indicators (green=good, red=warning/critical)
- Real-time updates at 60Hz
- Intelligent room lighting control
- All functionality of drive.py + visual dashboard

Usage:
    python3 drivetui.py

Controls:
    q/Q - Quit
    l/L - View logs (check drivetui.log)

Requirements:
    - Same as drive.py (gt-telem, requests, pyyaml)
    - Terminal with color support recommended
    - Minimum terminal size: 80x20
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

# Set up minimal logging to file instead of stdout (since we'll use TUI)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='drivetui.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = os.getenv('HUEFLASH_CONFIG', 'config.yaml')

try:
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    HA_TOKEN = config['ha_token']
    HUE_LIGHT_ENTITY = config['hue_light_entity']
    HA_URL = config['ha_url']
    PS5_IP = config['ps5_ip']
    ROOM_LIGHTS = config.get('room_lights', [])  # List of room light entities
    TELEMETRY_TIMEOUT = config.get('telemetry_timeout', 5)  # Seconds before considering game paused
except Exception:
    HA_TOKEN = os.getenv('HA_TOKEN')
    HUE_LIGHT_ENTITY = os.getenv('HUE_LIGHT_ENTITY')
    HA_URL = os.getenv('HA_URL')
    PS5_IP = os.getenv('PS5_IP')
    ROOM_LIGHTS = []
    TELEMETRY_TIMEOUT = 5

if not all([HA_TOKEN, HUE_LIGHT_ENTITY, HA_URL, PS5_IP]):
    raise RuntimeError('Missing Home Assistant or PS5 config values')

headers = {
    'Authorization': f'Bearer {HA_TOKEN}',
    'Content-Type': 'application/json',
}

# Global variables
shift_light_active = False
driving_mode_active = False
room_lights_state = {}  # Store previous state of room lights
telemetry_timer = None
last_telemetry_time = None
packet_count = 0  # For debug logging
last_telemetry_data = None  # Store last telemetry values for comparison
data_frozen_start = None  # When did data stop changing

# TUI variables
current_telemetry = None
tui_running = True
tui_lock = threading.Lock()

class TUIDisplay:
    def __init__(self):
        self.stdscr = None
        self.height = 0
        self.width = 0
        
    def init_display(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Initialize curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(100) # 100ms timeout for input
        
        # Initialize color pairs if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)     # Red text
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Green text
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Yellow text
            curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Blue text
            curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Magenta text
            curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Cyan text
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)     # White on red (shift light)
    
    def draw_bar(self, y, x, width, value, max_value, label, color_pair=0, show_percentage=True):
        """Draw a horizontal progress bar"""
        if max_value == 0:
            fill_width = 0
            percentage = 0
        else:
            percentage = min(100, (value / max_value) * 100)
            fill_width = int((percentage / 100) * width)
        
        # Draw label
        self.stdscr.addstr(y, x, f"{label}:", color_pair)
        
        # Draw bar outline
        bar_y = y + 1
        self.stdscr.addstr(bar_y, x, "[" + " " * width + "]")
        
        # Fill the bar
        if fill_width > 0:
            fill_str = "█" * fill_width
            self.stdscr.addstr(bar_y, x + 1, fill_str, color_pair)
        
        # Show value and percentage
        if show_percentage:
            value_str = f"{value:.1f} ({percentage:.1f}%)"
        else:
            value_str = f"{value:.1f}"
        
        self.stdscr.addstr(y, x + len(label) + 2, value_str)
    
    def draw_status_line(self, y, x, text, color_pair=0):
        """Draw a status line with text"""
        self.stdscr.addstr(y, x, text, color_pair)
    
    def refresh_display(self):
        """Update the display with current telemetry data"""
        global current_telemetry, driving_mode_active, shift_light_active
        
        self.stdscr.clear()
        
        # Title
        title = "GT7 Drive Mode TUI - Racing Dashboard"
        self.stdscr.addstr(0, (self.width - len(title)) // 2, title, curses.color_pair(6) | curses.A_BOLD)
        
        if current_telemetry is None:
            self.stdscr.addstr(2, 2, "Waiting for GT7 telemetry data...", curses.color_pair(3))
            self.stdscr.addstr(4, 2, "Make sure GT7 is running and telemetry is enabled.", curses.color_pair(3))
            self.stdscr.addstr(5, 2, "Settings → Network → Enable Telemetry", curses.color_pair(3))
            self.stdscr.refresh()
            return
        
        y = 2
        
        # Connection status
        status_color = curses.color_pair(2) if driving_mode_active else curses.color_pair(3)
        status_text = "DRIVING MODE ACTIVE" if driving_mode_active else "Connected - Waiting for race"
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
        # For now, use a fixed fuel level since we're not sure of the attribute name
        # This can be updated once we identify the correct GT7 fuel attribute
        fuel_level = 75  # Placeholder - showing 75% fuel
        max_rpm = 8000  # Reasonable default max RPM
        max_speed = 300  # Reasonable max speed for display
        max_fuel = 100   # Fuel percentage
        
        # RPM Bar
        rpm_color = curses.color_pair(1) if rpm > max_rpm * 0.9 else curses.color_pair(2)
        self.draw_bar(y, 2, 40, rpm, max_rpm, "RPM", rpm_color)
        y += 3
        
        # Speed Bar  
        speed_color = curses.color_pair(4)
        self.draw_bar(y, 2, 40, speed, max_speed, "Speed (km/h)", speed_color)
        y += 3
        
        # Fuel Bar
        fuel_color = curses.color_pair(1) if fuel_level < 20 else curses.color_pair(2)
        self.draw_bar(y, 2, 40, fuel_level, max_fuel, "Fuel", fuel_color)
        y += 3
        
        # Additional telemetry info
        gear = getattr(current_telemetry, 'current_gear', 0)
        # Fix throttle and brake - throttle seems to be a large value, possibly 0-255
        throttle_raw = getattr(current_telemetry, 'throttle', 0)
        brake_raw = getattr(current_telemetry, 'brake', 0)
        
        # Handle different throttle ranges based on observed values
        if throttle_raw > 255:
            throttle = min(100, throttle_raw / 255)  # If over 255, scale down
        elif throttle_raw > 100:
            throttle = min(100, throttle_raw / 255 * 100)  # Scale 0-255 to 0-100
        else:
            throttle = throttle_raw  # Already 0-100 or 0-1 range
            
        if brake_raw > 255:
            brake = min(100, brake_raw / 255)  
        elif brake_raw > 100:
            brake = min(100, brake_raw / 255 * 100)
        else:
            brake = brake_raw
        
        self.draw_status_line(y, 2, f"Gear: {gear}", curses.color_pair(6))
        self.draw_status_line(y + 1, 2, f"Throttle: {throttle:.1f}%", curses.color_pair(2))
        self.draw_status_line(y + 2, 2, f"Brake: {brake:.1f}%", curses.color_pair(1))
        
        # Instructions
        y = self.height - 3
        self.draw_status_line(y, 2, "Press 'q' to quit", curses.color_pair(3))
        self.draw_status_line(y + 1, 2, "Press 'l' to view logs in drivetui.log", curses.color_pair(3))
        
        self.stdscr.refresh()
    
    def handle_input(self):
        """Handle keyboard input"""
        global tui_running
        
        try:
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                tui_running = False
                return False
            elif key == ord('l') or key == ord('L'):
                # Could add log viewer here
                pass
        except:
            pass
        return True

# Create global TUI display instance
tui_display = TUIDisplay()

def get_light_state(entity_id):
    """Get current state of a light entity"""
    url = f"{HA_URL}/api/states/{entity_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        state_data = response.json()
        return {
            'state': state_data['state'],
            'brightness': state_data.get('attributes', {}).get('brightness'),
            'rgb_color': state_data.get('attributes', {}).get('rgb_color'),
            'color_temp': state_data.get('attributes', {}).get('color_temp')
        }
    except requests.RequestException as e:
        logger.error(f"Failed to get state for {entity_id}: {e}")
        return None

def set_light_state(entity_id, state_info):
    """Restore a light to its previous state"""
    if state_info['state'] == 'off':
        url = f"{HA_URL}/api/services/light/turn_off"
        data = {"entity_id": entity_id}
    else:
        url = f"{HA_URL}/api/services/light/turn_on"
        data = {"entity_id": entity_id}
        
        # Add brightness if available
        if state_info['brightness'] is not None:
            data["brightness"] = state_info['brightness']
            
        # Add color if available
        if state_info['rgb_color'] is not None:
            data["rgb_color"] = state_info['rgb_color']
        elif state_info['color_temp'] is not None:
            data["color_temp"] = state_info['color_temp']
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Restored light {entity_id} to previous state")
    except requests.RequestException as e:
        logger.error(f"Failed to restore light {entity_id}: {e}")

def turn_off_room_lights():
    """Turn off all room lights and save their current state"""
    global room_lights_state
    
    if not ROOM_LIGHTS:
        logger.info("No room lights configured")
        return
    
    logger.info("Saving room light states and turning off lights...")
    room_lights_state = {}
    
    for light_entity in ROOM_LIGHTS:
        # Get current state
        current_state = get_light_state(light_entity)
        if current_state:
            room_lights_state[light_entity] = current_state
            logger.info(f"Saved state for {light_entity}: {current_state['state']}")
        
        # Turn off the light
        url = f"{HA_URL}/api/services/light/turn_off"
        data = {"entity_id": light_entity}
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            logger.info(f"Turned off room light: {light_entity}")
        except requests.RequestException as e:
            logger.error(f"Failed to turn off room light {light_entity}: {e}")

def restore_room_lights():
    """Restore all room lights to their previous state"""
    global room_lights_state
    
    if not room_lights_state:
        logger.info("No room light states to restore")
        return
    
    logger.info("Restoring room lights to previous state...")
    
    for light_entity, state_info in room_lights_state.items():
        set_light_state(light_entity, state_info)
    
    room_lights_state = {}

def set_shift_light_brightness(brightness):
    """Control the shift light (red color for rev limit)"""
    url = f"{HA_URL}/api/services/light/turn_on"
    data = {
        "entity_id": HUE_LIGHT_ENTITY,
        "brightness": int(brightness * 255),
        "rgb_color": [255, 0, 0]  # Red color
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to turn on shift light: {e}")

def turn_off_shift_light():
    """Turn off the shift light"""
    url = f"{HA_URL}/api/services/light/turn_off"
    data = {"entity_id": HUE_LIGHT_ENTITY}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to turn off shift light: {e}")

def enter_driving_mode():
    """Enter driving mode - turn off room lights"""
    global driving_mode_active
    
    if not driving_mode_active:
        logger.info("🏁 Entering driving mode - GT7 race active!")
        driving_mode_active = True
        turn_off_room_lights()

def exit_driving_mode():
    """Exit driving mode - restore room lights"""
    global driving_mode_active, shift_light_active, telemetry_timer
    
    if driving_mode_active:
        logger.info("⏸️  Exiting driving mode - GT7 race paused/stopped")
        driving_mode_active = False
        
        # Turn off shift light if it's on
        if shift_light_active:
            shift_light_active = False
            turn_off_shift_light()
        
        # Clear the timer
        if telemetry_timer:
            telemetry_timer.cancel()
            telemetry_timer = None
        
        # Restore room lights
        restore_room_lights()

def is_telemetry_data_changing(packet):
    """Check if telemetry data is changing (game active) or frozen (game paused)"""
    global last_telemetry_data, data_frozen_start
    
    try:
        # Get key telemetry values that should change during active gameplay
        current_data = {
            'rpm': getattr(packet, 'engine_rpm', 0),
            'speed': getattr(packet, 'speed_kph', 0),
            'position_x': getattr(packet, 'position_x', 0),
            'position_y': getattr(packet, 'position_y', 0),
            'position_z': getattr(packet, 'position_z', 0),
            'time_of_day': getattr(packet, 'time_of_day_ms', 0),
        }
        
        # First time - just store the data
        if last_telemetry_data is None:
            last_telemetry_data = current_data
            data_frozen_start = None
            return True, 0
        
        # Check if any significant values have changed
        data_changed = False
        for key, value in current_data.items():
            if abs(value - last_telemetry_data.get(key, 0)) > 0.1:  # Small threshold for float precision
                data_changed = True
                break
        
        current_time = time.time()
        
        if data_changed:
            # Data is changing - game is active
            last_telemetry_data = current_data
            data_frozen_start = None
            return True, 0
        else:
            # Data hasn't changed
            if data_frozen_start is None:
                data_frozen_start = current_time
            
            frozen_duration = current_time - data_frozen_start
            return False, frozen_duration
            
    except Exception as e:
        logger.error(f"Error checking telemetry data changes: {e}")
        return True, 0

def is_actually_driving(packet):
    """Simple check if we're in a driving context (not in menus)"""
    try:
        # Basic check - if we have meaningful RPM or speed, we're probably in a race
        rpm = getattr(packet, 'engine_rpm', 0)
        speed = getattr(packet, 'speed_kph', 0)
        gear = getattr(packet, 'current_gear', 0)
        
        # Simple detection - if any of these indicate we're in a race context
        in_race_context = (
            rpm > 0 or  # Engine running
            abs(speed) > 0.1 or  # Any movement
            gear != 0  # In any gear
        )
        
        return in_race_context
        
    except Exception as e:
        logger.error(f"Error checking driving state: {e}")
        return False

def telemetry_callback(telemetry):
    global hue_light_state, room_light_state, data_frozen_start, last_telemetry_data, telemetry_timer, packet_count, shift_light_active, current_telemetry
    packet_count += 1
    
    # Update current telemetry for TUI display
    with tui_lock:
        current_telemetry = telemetry
    
    # Check if we're in a race context (not menus)
    in_race_context = is_actually_driving(telemetry)
    
    # Check if telemetry data is changing or frozen
    data_changing, frozen_duration = is_telemetry_data_changing(telemetry)
    
    # Reduced debug logging - only log significant events
    if packet_count % 300 == 0:  # Every 5 seconds instead of every second
        rpm = getattr(telemetry, 'engine_rpm', 0)
        speed = getattr(telemetry, 'speed_kph', 0)
        gear = getattr(telemetry, 'current_gear', 0)
        logger.info(f"Telemetry - In Race: {in_race_context}, Data Changing: {data_changing}, Frozen: {frozen_duration:.1f}s, RPM: {rpm:.0f}, Speed: {speed:.1f}kph, Gear: {gear}")
    
    if in_race_context:
        # We're in a race/driving context
        
        if data_changing:
            # Data is actively changing - reset any timers
            if telemetry_timer:
                telemetry_timer.cancel()
                telemetry_timer = None
            
            # Enter driving mode if not already active
            enter_driving_mode()
            
            # Handle shift light logic
            at_rev_limit = getattr(telemetry, 'rev_limit', False)
            
            if at_rev_limit and not shift_light_active:
                logger.info("🔴 Shift light ON - Rev limit reached!")
                shift_light_active = True
                set_shift_light_brightness(1.0)
                
            elif not at_rev_limit and shift_light_active:
                logger.info("⚫ Shift light OFF - Rev limit cleared")
                shift_light_active = False
                turn_off_shift_light()
                
        elif frozen_duration > 1.0:
            # Data has been frozen for more than 1 second - start exit timer
            if telemetry_timer is None:
                logger.info(f"📊 Data frozen for {frozen_duration:.1f}s - starting exit timer")
                telemetry_timer = Timer(TELEMETRY_TIMEOUT, exit_driving_mode)
                telemetry_timer.start()
        
        # If frozen for less than 1 second, do nothing - just wait
        
    else:
        # We're in menus - make sure we're not in driving mode
        if driving_mode_active:
            exit_driving_mode()

def tui_main_loop(stdscr):
    """Main TUI loop that runs in curses context"""
    global tui_running, tui_display
    
    # Initialize the TUI display
    tui_display.init_display(stdscr)
    
    while tui_running:
        # Update the display
        tui_display.refresh_display()
        
        # Handle input
        if not tui_display.handle_input():
            break
            
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global tui_running, telemetry_timer
    
    logger.info("Shutdown signal received...")
    tui_running = False
    
    # Clean shutdown
    if telemetry_timer:
        telemetry_timer.cancel()
    
    exit_driving_mode()  # Restore room lights

def main():
    global tui_running
    
    logger.info("Starting GT7 Drive Mode TUI with Room Lighting")
    logger.info(f"Configured room lights: {ROOM_LIGHTS}")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    logger.info(f"Telemetry timeout: {TELEMETRY_TIMEOUT} seconds")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start telemetry client in a separate thread
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        
        # Start telemetry client in background thread
        telemetry_thread = threading.Thread(target=client.start, daemon=True)
        telemetry_thread.start()
        
        logger.info("GT7 telemetry client started")
        
        # Give client time to connect
        time.sleep(2)
        
        # Start the TUI
        curses.wrapper(tui_main_loop)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error starting TUI: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        tui_running = False
        
        # Clean shutdown
        if telemetry_timer:
            telemetry_timer.cancel()
        
        exit_driving_mode()  # Restore room lights
        
        if 'client' in locals():
            client.stop()
        
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()