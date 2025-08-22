#!/usr/bin/env python3
"""
GT7 Stream Deck Mini Integration - Multi-Screen
===============================================

Displays GT7 telemetry data on Stream Deck Mini buttons with multiple screens:

📱 MAIN SCREEN (Default):
- Shift light indicator (red when at rev limit)
- GT7's built-in gear suggestions (for turns/optimal driving)
- Current gear display  
- Speed display
- RPM with visual gauge
- Room lighting status

🎮 GEAR SCREEN:
- Visual gear indicators (buttons 1-6 for gears 1-6)
- Current gear: Bright green (or flashing red at rev limit)
- GT7 suggested gear: Bright orange
- Other gears: Dark/off
- No text - purely visual color coding

Features:
- Press ANY button to cycle between screens
- Real-time telemetry updates on Stream Deck buttons
- Visual gauges and progress bars on button displays
- GT7's native gear recommendations (blue=upshift, orange=downshift, green=current)
- All room lighting automation from drive.py
- Multi-screen support with button press switching

Requirements:
- streamdeck library: pip install streamdeck
- PIL (Pillow): pip install pillow
- Same GT7 requirements as other scripts

Usage:
    python3 streamdeck_gt7.py

Screen Layouts:
    Main Screen:
    [SHIFT] [GT7] [GEAR]
    [SPEED] [RPM] [STATUS]
    
    Gear Screen:
    [  1  ] [ 2  ] [ 3  ]
    [  4  ] [ 5  ] [ 6  ]
"""

import os
import time
import threading
import signal
import sys
import argparse
import socket
import subprocess
from PIL import Image, ImageDraw, ImageFont
import requests
import logging- Visual gauges and progress bars on button displays
- GT7's native gear recommendations (blue=upshift, orange=downshift, green=current)
- All room lighting automation from drive.py
- Multi-screen support with button press switching

Requirements:
- streamdeck library: pip install streamdeck
- PIL (Pillow): pip install pillow
- Same GT7 requirements as other scripts

Usage:
    python3 streamdeck_gt7.py

Screen Layouts:
    Main Screen:
    [SHIFT] [GT7] [GEAR]
    [SPEED] [RPM] [STATUS]
    
    Gear Screen:
    [  1  ] [ 2  ] [ 3  ]
    [  4  ] [ 5  ] [ 6  ]
"""

import os
import time
import threading
import signal
import sys
import argparse
import socket
from PIL import Image, ImageDraw, ImageFont
import requests
import logging

# Stream Deck imports
try:
    from StreamDeck.DeviceManager import DeviceManager
    from StreamDeck.ImageHelpers import PILHelper
    STREAMDECK_AVAILABLE = True
except ImportError:
    STREAMDECK_AVAILABLE = False
    print("⚠️  StreamDeck library not found. Running in simulation mode.")
    print("Install with: pip install streamdeck")

from gt_telem.turismo_client import TurismoClient
from threading import Timer

# Set up logging to file
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='streamdeck_gt7.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Load config (same as other scripts)
CONFIG_PATH = os.getenv('HUEFLASH_CONFIG', 'config.yaml')

try:
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    HA_TOKEN = config['ha_token']
    HUE_LIGHT_ENTITY = config['hue_light_entity']
    HA_URL = config['ha_url']
    PS5_IP = config['ps5_ip']
    ROOM_LIGHTS = config.get('room_lights', [])
    TELEMETRY_TIMEOUT = config.get('telemetry_timeout', 5)
except Exception as e:
    logger.error(f"Config error: {e}")
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

# Global variables (same as drive.py)
shift_light_active = False
driving_mode_active = False
room_lights_state = {}
telemetry_timer = None
last_telemetry_time = None
packet_count = 0
last_telemetry_data = None
data_frozen_start = None

# Stream Deck variables
current_telemetry = None
streamdeck = None
running = True
telemetry_lock = threading.Lock()
simulation_mode = False

def wake_ps5(ps5_ip):
    """
    Wake up PS5 using Wake-on-LAN
    Note: PS5 must have 'Enable turning on PS5 from network' enabled in settings
    """
    try:
        print(f"🔄 Attempting to wake PS5 at {ps5_ip}...")
        logger.info(f"Attempting to wake PS5 at {ps5_ip}")
        
        # Try to ping the PS5 first to see if it wakes up from that
        ping_result = subprocess.run(['ping', '-c', '1', '-W', '1000', ps5_ip], 
                                   capture_output=True, text=True)
        
        if ping_result.returncode == 0:
            print("✅ PS5 appears to be responding to ping")
            return True
            
        # If ping doesn't work, try a UDP wake packet
        # Send UDP packets to common PS5 ports to trigger wake-up
        wake_ports = [9302, 9303, 9304]  # PS5 discovery and wake ports
        
        for port in wake_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                # Send a discovery-like packet which might wake the PS5
                wake_packet = b"WAKE * HTTP/1.1\ndevice-discovery-protocol-version:00030010"
                sock.sendto(wake_packet, (ps5_ip, port))
                sock.close()
                
                print(f"📡 Sent wake packet to {ps5_ip}:{port}")
                
            except Exception as e:
                logger.debug(f"Failed to send wake packet to port {port}: {e}")
        
        # Wait a moment and try ping again
        time.sleep(3)
        ping_result = subprocess.run(['ping', '-c', '1', '-W', '2000', ps5_ip], 
                                   capture_output=True, text=True)
        
        if ping_result.returncode == 0:
            print("✅ PS5 wake-up successful!")
            logger.info("PS5 wake-up successful")
            return True
        else:
            print("⚠️  PS5 may not have responded to wake-up attempt")
            print("💡 Make sure 'Enable turning on PS5 from network' is enabled in PS5 settings")
            logger.warning("PS5 did not respond to wake-up attempt")
            return False
            
    except Exception as e:
        print(f"❌ Failed to wake PS5: {e}")
        logger.error(f"Failed to wake PS5: {e}")
        return False

# Screen layouts for Stream Deck Mini (6 buttons: 3x2)
SCREEN_LAYOUTS = {
    "main": {
        0: "shift",        # Top left
        1: "suggested",    # Top middle (suggested gear)
        2: "gear",         # Top right
        3: "speed",        # Bottom left
        4: "rpm",          # Bottom middle
        5: "status"        # Bottom right
    },
    "gears": {
        0: "gear1",        # Top left
        1: "gear2",        # Top middle
        2: "gear3",        # Top right
        3: "gear4",        # Bottom left
        4: "gear5",        # Bottom middle
        5: "gear6"         # Bottom right
    }
}

# Current active screen
current_screen = "main"

class StreamDeckGT7:
    def __init__(self, simulate=False):
        self.deck = None
        self.button_images = {}
        self.simulate = simulate
        self.current_screen = "main"
        
    def initialize_streamdeck(self):
        """Initialize Stream Deck connection"""
        if self.simulate or not STREAMDECK_AVAILABLE:
            logger.info("Running in simulation mode")
            print("🔄 Running in Stream Deck simulation mode")
            print("📱 Virtual Stream Deck Mini initialized (3x2 layout)")
            self.create_initial_buttons()
            return True
            
        try:
            streamdecks = DeviceManager().enumerate()
            if not streamdecks:
                logger.error("No Stream Deck devices found")
                print("❌ No Stream Deck devices found")
                print("Make sure your Stream Deck Mini is:")
                print("  - Connected via USB")
                print("  - Not being used by the official Stream Deck software")
                print("💡 Run with --simulate flag to use simulation mode")
                return False
                
            self.deck = streamdecks[0]
            self.deck.open()
            self.deck.reset()
            
            # Set brightness
            self.deck.set_brightness(50)
            
            # Set up button press callback
            self.deck.set_key_callback(self.button_callback)
            
            logger.info(f"Connected to {self.deck.deck_type()}")
            logger.info(f"Buttons: {self.deck.key_count()}")
            print(f"✅ Connected to {self.deck.deck_type()}")
            print("🔄 Press any button to cycle screens")
            
            # Initialize button images
            self.create_initial_buttons()
            
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing Stream Deck: {e}")
            print("❌ Permission denied accessing Stream Deck")
            print("💡 Try running with: sudo python3 streamdeck_gt7.py")
            print("💡 Or close the Stream Deck software if it's running")
            print("💡 Or run with --simulate flag to use simulation mode")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Stream Deck: {e}")
            print(f"❌ Failed to initialize Stream Deck: {e}")
            print("💡 Run with --simulate flag to use simulation mode")
            return False
    
    def create_button_image(self, text, value="", color=(255, 255, 255), bg_color=(0, 0, 0), progress=None):
        """Create a button image with text and optional progress bar"""
        # Stream Deck Mini buttons are 80x80 pixels
        image = Image.new('RGB', (80, 80), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 10)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw title text
        text_bbox = draw.textbbox((0, 0), text, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (80 - text_width) // 2
        draw.text((text_x, 5), text, font=font_large, fill=color)
        
        # Draw value
        if value:
            value_bbox = draw.textbbox((0, 0), str(value), font=font_small)
            value_width = value_bbox[2] - value_bbox[0]
            value_x = (80 - value_width) // 2
            draw.text((value_x, 25), str(value), font=font_small, fill=color)
        
        # Draw progress bar if provided
        if progress is not None:
            bar_width = 60
            bar_height = 8
            bar_x = (80 - bar_width) // 2
            bar_y = 45
            
            # Background bar
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                         outline=(100, 100, 100), fill=(50, 50, 50))
            
            # Progress fill
            if progress > 0:
                fill_width = int((progress / 100) * bar_width)
                fill_color = (255, 0, 0) if progress > 90 else (0, 255, 0)
                draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 
                             fill=fill_color)
            
            # Progress percentage
            progress_text = f"{progress:.0f}%"
            prog_bbox = draw.textbbox((0, 0), progress_text, font=font_small)
            prog_width = prog_bbox[2] - prog_bbox[0]
            prog_x = (80 - prog_width) // 2
            draw.text((prog_x, 60), progress_text, font=font_small, fill=color)
        
        return image
    
    def create_initial_buttons(self):
        """Create initial button layout for current screen"""
        if self.current_screen == "main":
            self.create_main_screen()
        elif self.current_screen == "gears":
            self.create_gear_screen()
    
    def create_main_screen(self):
        """Create the main telemetry screen"""
        if self.simulate:
            print("🔄 Initializing virtual Stream Deck buttons...")
            print("┌────────┬────────┬────────┐")
            print("│ SHIFT  │  GT7   │ GEAR   │")
            print("│ Ready  │   N    │   N    │")
            print("├────────┼────────┼────────┤")
            print("│ SPEED  │  RPM   │STATUS  │")
            print("│ 0 km/h │   0    │Waiting │")
            print("└────────┴────────┴────────┘")
            return
            
        buttons = {
            "shift": self.create_button_image("SHIFT", "Ready", color=(255, 255, 255)),
            "suggested": self.create_button_image("GT7", "N", color=(255, 255, 255)),
            "gear": self.create_button_image("GEAR", "N"),
            "speed": self.create_button_image("SPEED", "0 km/h"),
            "rpm": self.create_button_image("RPM", "0", progress=0),
            "status": self.create_button_image("STATUS", "Waiting", color=(255, 255, 0))
        }
        
        layout = SCREEN_LAYOUTS[self.current_screen]
        for button_id, button_type in layout.items():
            if button_type in buttons:
                # Convert PIL image to Stream Deck format
                image = PILHelper.to_native_format(self.deck, buttons[button_type])
                self.deck.set_key_image(button_id, image)
    
    def create_gear_screen(self):
        """Create the gear visualization screen"""
        if self.simulate:
            print("🔄 Initializing Gear Screen...")
            print("┌────────┬────────┬────────┐")
            print("│   1    │   2    │   3    │")
            print("│        │        │        │")
            print("├────────┼────────┼────────┤")
            print("│   4    │   5    │   6    │")
            print("│        │        │        │")
            print("└────────┴────────┴────────┘")
            return
            
        # Create gear buttons 1-6 (no text, just colors)
        for gear_num in range(1, 7):
            button_id = gear_num - 1  # buttons 0-5 for gears 1-6
            # Default to dark background
            image = self.create_button_image("", "", color=(80, 80, 80), bg_color=(20, 20, 20))
            
            if self.deck:
                native_image = PILHelper.to_native_format(self.deck, image)
                self.deck.set_key_image(button_id, native_image)
    
    def button_callback(self, deck, key, state):
        """Handle button press events - any button press switches screens"""
        if state:  # Only handle button press (not release)
            self.switch_screen()
    
    def switch_screen(self):
        """Switch to the next screen"""
        screens = list(SCREEN_LAYOUTS.keys())
        current_index = screens.index(self.current_screen)
        next_index = (current_index + 1) % len(screens)
        self.current_screen = screens[next_index]
        
        print(f"🔄 Switching to {self.current_screen} screen")
        
        # Recreate the screen layout
        self.create_initial_buttons()
        
        # Update display if we have telemetry data
        if current_telemetry is not None:
            self.update_telemetry_display()
    
    def update_button(self, button_type, text, value="", color=(255, 255, 255), bg_color=(0, 0, 0), progress=None):
        """Update a specific button"""
        if self.simulate:
            # Simulate button update in console
            self.simulate_button_update(button_type, text, value, progress)
            return
            
        try:
            # Find button ID for this type in current screen layout
            button_id = None
            current_layout = SCREEN_LAYOUTS.get(self.current_screen, {})
            for bid, btype in current_layout.items():
                if btype == button_type:
                    button_id = bid
                    break
            
            if button_id is None:
                return
            
            # Create new image
            image = self.create_button_image(text, value, color, bg_color, progress)
            
            # Convert and set
            native_image = PILHelper.to_native_format(self.deck, image)
            self.deck.set_key_image(button_id, native_image)
            
        except Exception as e:
            logger.error(f"Failed to update button {button_type}: {e}")
    
    def simulate_button_update(self, button_type, text, value="", progress=None):
        """Simulate button update in console (for testing without hardware)"""
        # Create a visual representation
        if not hasattr(self, 'button_cache'):
            self.button_cache = {}
            
        if button_type == "rpm":
            bar = self.create_progress_bar(progress) if progress is not None else ""
            speed_val = self.button_cache.get('speed', ' ')
            gear_val = self.button_cache.get('gear', ' ')
            print(f"\r│ {text:^6} │ {speed_val:^6} │ {gear_val:^6} │", end="", flush=True)
        elif button_type == "speed":
            self.button_cache['speed'] = value[:6]
        elif button_type == "gear":
            self.button_cache['gear'] = value[:6]
        elif button_type == "shift":
            shift_symbol = "🔴" if "NOW" in value else "⚪"
            self.button_cache['shift'] = f"{shift_symbol} {value}"
    
    def create_progress_bar(self, progress):
        """Create a simple ASCII progress bar"""
        if progress is None:
            return ""
        bars = int(progress / 20)  # 5 bars max
        return "█" * bars + "░" * (5 - bars)
    
    def update_telemetry_display(self):
        """Update all buttons with current telemetry data"""
        global current_telemetry, shift_light_active, driving_mode_active
        
        if current_telemetry is None:
            return
            
        if self.current_screen == "main":
            self.update_main_screen_telemetry()
        elif self.current_screen == "gears":
            self.update_gear_screen_telemetry()
    
    def update_main_screen_telemetry(self):
        """Update main screen with telemetry data"""
        global current_telemetry, shift_light_active, driving_mode_active
        
        with telemetry_lock:
            # Get telemetry values
            rpm = getattr(current_telemetry, 'engine_rpm', 0)
            speed = getattr(current_telemetry, 'speed_kph', 0)
            gear = getattr(current_telemetry, 'current_gear', 0)
            throttle = getattr(current_telemetry, 'throttle', 0)
            # Get GT7's suggested gear directly from the game
            suggested_gear_num = getattr(current_telemetry, 'suggested_gear', 0)
            
            # Handle throttle scaling (GT7 sometimes gives values like 25500 instead of 100)
            if throttle > 255:
                throttle = throttle / 255.0
            throttle = min(100, max(0, throttle))
            
            # 1. Shift light (Top left)
            if shift_light_active:
                self.update_button("shift", "SHIFT!", "NOW!", (255, 255, 255), (255, 0, 0))
            else:
                self.update_button("shift", "SHIFT", "Ready", (255, 255, 255), (0, 0, 0))
            
            # 2. GT7's suggested gear (Top middle)
            # Format the suggested gear display
            # GT7 sends invalid values (like 15) when there's no suggestion
            if suggested_gear_num > 8 or suggested_gear_num < -1:
                # No valid suggestion - show empty
                suggested_text = ""
                suggested_color = (80, 80, 80)  # Dark gray for no suggestion
            elif suggested_gear_num == 0:
                suggested_text = "N"
                suggested_color = (255, 255, 255)  # White for neutral
            elif suggested_gear_num < 0:
                suggested_text = "R"
                suggested_color = (255, 100, 100)  # Light red for reverse
            else:
                suggested_text = str(suggested_gear_num)
                # Color code based on comparison with current gear
                if suggested_gear_num > gear:
                    suggested_color = (100, 150, 255)  # Blue for upshift
                elif suggested_gear_num < gear:
                    suggested_color = (255, 165, 0)   # Orange for downshift
                else:
                    suggested_color = (0, 255, 0)     # Green when suggested = current
            
            self.update_button("suggested", "GT7", suggested_text, suggested_color)
            
            # 3. Current gear (Top right)
            gear_text = "R" if gear < 0 else "N" if gear == 0 else str(gear)
            self.update_button("gear", "GEAR", gear_text, (0, 255, 0))
            
            # 4. Speed (Bottom left)
            self.update_button("speed", "SPEED", f"{speed:.0f} km/h", (0, 150, 255))
            
            # 5. RPM (Bottom middle)
            max_rpm = 8000
            rpm_percent = min(100, (rpm / max_rpm) * 100)
            rpm_color = (255, 0, 0) if rpm_percent > 90 else (255, 255, 255)
            self.update_button("rpm", "RPM", f"{rpm:.0f}", rpm_color, progress=rpm_percent)
            
            # 6. Status (Bottom right)
            if driving_mode_active:
                self.update_button("status", "STATUS", "Active", (0, 255, 0))
            else:
                self.update_button("status", "STATUS", "Waiting", (255, 255, 0))
    
    def update_gear_screen_telemetry(self):
        """Update gear screen with visual gear indicators"""
        global current_telemetry, shift_light_active
        
        with telemetry_lock:
            rpm = getattr(current_telemetry, 'engine_rpm', 0)
            gear = getattr(current_telemetry, 'current_gear', 0)
            suggested_gear_num = getattr(current_telemetry, 'suggested_gear', 0)
            
            # Update each gear button (1-6)
            for gear_num in range(1, 7):
                button_id = gear_num - 1  # buttons 0-5 for gears 1-6
                
                # Determine button color based on current state
                if gear == gear_num:
                    # Current gear - bright green (or flashing red if at rev limit)
                    if shift_light_active:
                        color = (255, 0, 0)  # Flash red at rev limit
                        bg_color = (255, 0, 0)
                    else:
                        color = (0, 255, 0)  # Bright green for current gear
                        bg_color = (0, 128, 0)
                elif suggested_gear_num == gear_num and suggested_gear_num > 0 and suggested_gear_num <= 8:
                    # GT7 suggested gear - bright orange
                    color = (255, 165, 0)
                    bg_color = (128, 82, 0)
                else:
                    # Not current, not suggested - dark
                    color = (80, 80, 80)
                    bg_color = (20, 20, 20)
                
                # Create button with no text (just color)
                image = self.create_button_image("", "", color, bg_color)
                
                if not self.simulate and self.deck:
                    native_image = PILHelper.to_native_format(self.deck, image)
                    self.deck.set_key_image(button_id, native_image)
                elif self.simulate:
                    # Show gear status in simulation
                    status = "🟢" if gear == gear_num else "🟠" if suggested_gear_num == gear_num else "⚫"
                    if gear_num == 1:
                        print(f"\rGears: {status}", end="")
                    else:
                        print(f" {status}", end="")
                    if gear_num == 6:
                        print("", flush=True)
    
    def close(self):
        """Close Stream Deck connection"""
        if self.deck:
            self.deck.reset()
            self.deck.close()
            print("📱 Stream Deck connection closed")
        elif self.simulate:
            print("🔄 Virtual Stream Deck simulation stopped")

# Initialize Stream Deck
stream_deck_gt7 = None

# Copy all the lighting functions from drive.py
def get_light_state(entity_id):
    """Get current state of a light"""
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get light state for {entity_id}: {e}")
        return None

def set_light_state(entity_id, state, brightness=None, rgb_color=None):
    """Set light state (on/off) with optional brightness and color"""
    try:
        if state == "on":
            url = f"{HA_URL}/api/services/light/turn_on"
            data = {"entity_id": entity_id}
            if brightness is not None:
                data["brightness"] = int(brightness * 255)
            if rgb_color is not None:
                data["rgb_color"] = rgb_color
        else:
            url = f"{HA_URL}/api/services/light/turn_off"
            data = {"entity_id": entity_id}
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to set light state for {entity_id}: {e}")
        return False

def set_shift_light_brightness(brightness):
    """Control the shift light (red color for rev limit)"""
    return set_light_state(HUE_LIGHT_ENTITY, "on", brightness, [255, 0, 0])

def turn_off_shift_light():
    """Turn off the shift light"""
    return set_light_state(HUE_LIGHT_ENTITY, "off")

def save_and_turn_off_room_lights():
    """Save current room light states and turn them off"""
    global room_lights_state
    
    logger.info("Saving room light states and turning off lights...")
    room_lights_state.clear()
    
    for light_entity in ROOM_LIGHTS:
        current_state = get_light_state(light_entity)
        if current_state:
            room_lights_state[light_entity] = current_state['state']
            logger.info(f"Saved state for {light_entity}: {current_state['state']}")
            
            if current_state['state'] == 'on':
                if set_light_state(light_entity, "off"):
                    logger.info(f"Turned off room light: {light_entity}")

def restore_room_lights():
    """Restore room lights to their previous states"""
    global room_lights_state
    
    logger.info("Restoring room lights to previous state...")
    
    for light_entity, previous_state in room_lights_state.items():
        if set_light_state(light_entity, previous_state):
            logger.info(f"Restored light {light_entity} to previous state")

def enter_driving_mode():
    """Enter driving mode - turn off room lights"""
    global driving_mode_active
    
    if not driving_mode_active:
        driving_mode_active = True
        logger.info("🏁 Entering driving mode - GT7 race active!")
        save_and_turn_off_room_lights()

def exit_driving_mode():
    """Exit driving mode - restore room lights"""
    global driving_mode_active
    
    if driving_mode_active:
        driving_mode_active = False
        logger.info("⏸️  Exiting driving mode - GT7 race paused/stopped")
        restore_room_lights()

def is_telemetry_data_changing(current_data):
    """Check if telemetry data is changing (not paused/frozen)"""
    global last_telemetry_data, data_frozen_start
    
    try:
        current_time = time.time()
        
        # Create a snapshot of key telemetry values that should change during gameplay
        current_snapshot = {
            'rpm': getattr(current_data, 'engine_rpm', 0),
            'speed': getattr(current_data, 'speed_kph', 0),
            'position_x': getattr(current_data, 'position_x', 0),
            'position_y': getattr(current_data, 'position_y', 0), 
            'position_z': getattr(current_data, 'position_z', 0),
            'time_of_day': getattr(current_data, 'time_of_day_ms', 0)
        }
        
        # Compare with last snapshot
        if last_telemetry_data is None:
            last_telemetry_data = current_snapshot
            data_frozen_start = None
            return True, 0
        
        # Check if any values have changed
        data_changed = any(
            abs(current_snapshot[key] - last_telemetry_data[key]) > 0.01
            for key in current_snapshot.keys()
        )
        
        # Update last data
        last_telemetry_data = current_snapshot
        
        if data_changed:
            # Data is changing
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
        rpm = getattr(packet, 'engine_rpm', 0)
        speed = getattr(packet, 'speed_kph', 0)
        gear = getattr(packet, 'current_gear', 0)
        
        in_race_context = (
            rpm > 0 or
            abs(speed) > 0.1 or
            gear != 0
        )
        
        return in_race_context
        
    except Exception as e:
        logger.error(f"Error checking driving context: {e}")
        return False

def telemetry_callback(telemetry):
    """Main telemetry callback with Stream Deck updates"""
    global current_telemetry, shift_light_active, packet_count, telemetry_timer
    packet_count += 1
    
    # Update current telemetry for Stream Deck
    with telemetry_lock:
        current_telemetry = telemetry
    
    # Check driving context and data changes
    in_race_context = is_actually_driving(telemetry)
    data_changing, frozen_duration = is_telemetry_data_changing(telemetry)
    
    # Reduced logging
    if packet_count % 300 == 0:  # Every 5 seconds
        rpm = getattr(telemetry, 'engine_rpm', 0)
        speed = getattr(telemetry, 'speed_kph', 0)
        gear = getattr(telemetry, 'current_gear', 0)
        logger.info(f"Telemetry - In Race: {in_race_context}, Data Changing: {data_changing}, RPM: {rpm:.0f}, Speed: {speed:.1f}kph, Gear: {gear}")
    
    if in_race_context:
        if data_changing:
            if telemetry_timer:
                telemetry_timer.cancel()
                telemetry_timer = None
            
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
                turn_off_shift_light()
                
        elif frozen_duration > 1.0:
            if telemetry_timer is None:
                logger.info(f"📊 Data frozen for {frozen_duration:.1f}s - starting exit timer")
                telemetry_timer = Timer(TELEMETRY_TIMEOUT, exit_driving_mode)
                telemetry_timer.start()
    else:
        # Not in race context
        if driving_mode_active:
            exit_driving_mode()
        
        if shift_light_active:
            shift_light_active = False
            turn_off_shift_light()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running, telemetry_timer, stream_deck_gt7
    
    print("\n🛑 Shutdown signal received...")
    logger.info("Shutdown signal received...")
    running = False
    
    if telemetry_timer:
        telemetry_timer.cancel()
    
    exit_driving_mode()
    
    if stream_deck_gt7:
        stream_deck_gt7.close()
    
    print("👋 Goodbye!")
    sys.exit(0)

def main():
    """Main function"""
    global running, stream_deck_gt7
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GT7 Stream Deck Integration')
    parser.add_argument('--simulate', action='store_true', 
                       help='Run in simulation mode without hardware')
    args = parser.parse_args()
    
    logger.info("Starting GT7 Stream Deck integration")
    logger.info(f"Configured room lights: {ROOM_LIGHTS}")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    
    # Initialize Stream Deck
    stream_deck_gt7 = StreamDeckGT7(simulate=args.simulate)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize Stream Deck
    if not stream_deck_gt7.initialize_streamdeck():
        logger.error("Failed to initialize Stream Deck")
        return
    
    try:
        # Start GT7 telemetry
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        
        telemetry_thread = threading.Thread(target=client.start, daemon=True)
        telemetry_thread.start()
        
        logger.info("GT7 telemetry client started")
        if args.simulate:
            logger.info("Stream Deck simulation mode running...")
            print("🎮 GT7 Stream Deck simulation running...")
            print("📊 Telemetry data will be displayed below:")
            print("🛑 Press Ctrl+C to stop")
        else:
            logger.info("Stream Deck GT7 dashboard running...")
            print("🎮 GT7 Stream Deck dashboard running...")
            print("🛑 Press Ctrl+C to stop")
        
        # Main loop - update Stream Deck display
        try:
            loop_count = 0
            while running:
                stream_deck_gt7.update_telemetry_display()
                
                # Check for shutdown more frequently
                for i in range(10):  # Check 10 times per 0.1 second
                    if not running:
                        break
                    time.sleep(0.01)  # 10ms sleep each time
                
                loop_count += 1
                if loop_count % 100 == 0:  # Every 10 seconds
                    logger.info("Stream Deck update loop running...")
                    
        except KeyboardInterrupt:
            print("\n🛑 Ctrl+C detected, shutting down...")
            running = False
            
    except KeyboardInterrupt:
        print("\n🛑 Ctrl+C detected during startup, shutting down...")
        running = False
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("🔄 Cleaning up...")
        logger.info("Shutting down...")
        running = False
        
        if telemetry_timer:
            telemetry_timer.cancel()
        
        # Stop telemetry client
        if 'client' in locals():
            try:
                client.stop()
                logger.info("Telemetry client stopped")
            except Exception as e:
                logger.error(f"Error stopping telemetry client: {e}")
        
        exit_driving_mode()
        if stream_deck_gt7:
            stream_deck_gt7.close()
        
        if 'client' in locals():
            try:
                client.stop()
            except:
                pass
        
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()
