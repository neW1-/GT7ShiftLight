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
- GT7's native gear recommendations
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
from threading import Timer
import signal
import sys
import argparse
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

# GT7 telemetry imports
from gt_telem.turismo_client import TurismoClient
from gt_telem.errors.playstation_errors import PlayStatonOnStandbyError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    ROOM_LIGHTS = config.get('room_lights', [])
    PS5_IP = config['ps5_ip']
    
except FileNotFoundError:
    logger.warning(f"Config file {CONFIG_PATH} not found, using environment variables")
    HA_TOKEN = os.getenv('HA_TOKEN')
    HUE_LIGHT_ENTITY = os.getenv('HUE_LIGHT_ENTITY')
    HA_URL = os.getenv('HA_URL')
    ROOM_LIGHTS = os.getenv('ROOM_LIGHTS', '').split(',') if os.getenv('ROOM_LIGHTS') else []
    PS5_IP = os.getenv('PS5_IP')
except ImportError:
    logger.warning("PyYAML not found, using environment variables")
    HA_TOKEN = os.getenv('HA_TOKEN')
    HUE_LIGHT_ENTITY = os.getenv('HUE_LIGHT_ENTITY')
    HA_URL = os.getenv('HA_URL')
    ROOM_LIGHTS = os.getenv('ROOM_LIGHTS', '').split(',') if os.getenv('ROOM_LIGHTS') else []
    PS5_IP = os.getenv('PS5_IP')

if not all([HA_TOKEN, HUE_LIGHT_ENTITY, HA_URL, PS5_IP]):
    raise RuntimeError('Missing Home Assistant or PS5 config values')

# Global state variables
driving_mode_active = False
shift_light_active = False
last_light_state = None
telemetry_timer = None
last_telemetry_time = None
packet_count = 0
last_telemetry_data = None
data_frozen_start = None
last_status = None  # Track last printed status

# Stream Deck variables
current_telemetry = None
streamdeck = None
running = True
telemetry_lock = threading.Lock()
simulation_mode = False
gt7_client = None  # Add global client variable

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

class StreamDeckGT7:
    def __init__(self, simulate=False, brightness=50, rotation=0):
        self.deck = None
        self.button_images = {}
        self.simulate = simulate
        self.current_screen = "main"
        self.brightness = brightness
        self.rotation = rotation
        
        # Create rotated button mappings based on rotation
        self.setup_rotated_layouts()
        
    def setup_rotated_layouts(self):
        """Create button layouts adjusted for rotation"""
        # Original layouts (0 degrees)
        original_main = {
            0: "shift",        # Top left
            1: "suggested",    # Top middle (suggested gear)
            2: "gear",         # Top right
            3: "speed",        # Bottom left
            4: "rpm",          # Bottom middle
            5: "status"        # Bottom right
        }
        
        original_gears = {
            0: "gear1",        # Top left
            1: "gear2",        # Top middle
            2: "gear3",        # Top right
            3: "gear4",        # Bottom left
            4: "gear5",        # Bottom middle
            5: "gear6"         # Bottom right
        }
        
        # H-shifter layout (3rd screen) - matches real H-shifter gate pattern
        original_h_shifter = {
            0: "gear1",        # Button 1: Gear 1
            1: "gear3",        # Button 2: Gear 3  
            2: "gear5",        # Button 3: Gear 5
            3: "gear2",        # Button 4: Gear 2
            4: "gear4",        # Button 5: Gear 4
            5: "gear6"         # Button 6: Gear 6
        }
        
        # Apply rotation mapping
        if self.rotation == 0:
            self.rotated_main = original_main
            self.rotated_gears = original_gears
            self.rotated_h_shifter = original_h_shifter
        elif self.rotation == 90:  # 90° clockwise
            # Custom button mapping with gear3 and gear4 swapped
            # 0->2, 1->5, 2->1, 3->4, 4->0, 5->3
            rotation_map = {0: 2, 1: 5, 2: 1, 3: 4, 4: 0, 5: 3}
            self.rotated_main = {rotation_map[k]: v for k, v in original_main.items()}
            self.rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
            self.rotated_h_shifter = {rotation_map[k]: v for k, v in original_h_shifter.items()}
        elif self.rotation == 180:  # 180° rotation
            # Button mapping for 180° rotation: [0,1,2] -> [5,4,3]
            #                                    [3,4,5] -> [2,1,0]
            rotation_map = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0}
            self.rotated_main = {rotation_map[k]: v for k, v in original_main.items()}
            self.rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
            self.rotated_h_shifter = {rotation_map[k]: v for k, v in original_h_shifter.items()}
        elif self.rotation == 270:  # 270° clockwise (90° counter-clockwise)
            # Correct mapping: G1->4, G2->1, G3->5, G4->2, G5->6, G6->3
            rotation_map = {0: 3, 1: 0, 2: 4, 3: 1, 4: 5, 5: 2}
            self.rotated_main = {rotation_map[k]: v for k, v in original_main.items()}
            self.rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
            self.rotated_h_shifter = {rotation_map[k]: v for k, v in original_h_shifter.items()}
        
        # Store the current layouts
        self.screen_layouts = {
            "main": self.rotated_main,
            "gears": self.rotated_gears,
            "h_shifter": self.rotated_h_shifter
        }
    
    def print_rotated_main_layout(self):
        """Print the main screen layout adjusted for rotation"""
        # Create a mapping of button positions to labels
        layout = self.screen_layouts["main"]
        labels = {
            "shift": "SHIFT", "suggested": "GT7", "gear": "GEAR",
            "speed": "SPEED", "rpm": "RPM", "status": "STATUS"
        }
        values = {
            "shift": "Ready", "suggested": "N", "gear": "N", 
            "speed": "0km/h", "rpm": "0", "status": "Wait"
        }
        
        # Create 3x2 grid based on rotated layout
        grid_labels = [""] * 6
        grid_values = [""] * 6
        
        for button_id, button_type in layout.items():
            grid_labels[button_id] = labels.get(button_type, "")
            grid_values[button_id] = values.get(button_type, "")
        
        print("┌────────┬────────┬────────┐")
        print(f"│{grid_labels[0]:^8}│{grid_labels[1]:^8}│{grid_labels[2]:^8}│")
        print(f"│{grid_values[0]:^8}│{grid_values[1]:^8}│{grid_values[2]:^8}│")
        print("├────────┼────────┼────────┤")
        print(f"│{grid_labels[3]:^8}│{grid_labels[4]:^8}│{grid_labels[5]:^8}│")
        print(f"│{grid_values[3]:^8}│{grid_values[4]:^8}│{grid_values[5]:^8}│")
        print("└────────┴────────┴────────┘")
        if self.rotation != 0:
            print(f"   (Rotated {self.rotation}°)")
    
    def print_rotated_h_shifter_layout(self):
        """Print the H-shifter screen layout adjusted for rotation"""
        # Create a mapping of button positions to gear labels
        layout = self.screen_layouts["h_shifter"]
        
        # Create display grid
        grid = [["?", "?", "?"], ["?", "?", "?"]]
        
        for button_id, gear_type in layout.items():
            row = 0 if button_id < 3 else 1
            col = button_id % 3
            # Extract gear number from gear_type (e.g., "gear1" -> "1")
            gear_num = gear_type.replace("gear", "")
            grid[row][col] = f"G{gear_num}"
        
        print(f"\nH-Shifter Screen Layout (rotation {self.rotation}°):")
        print(f"[{grid[0][0]}] [{grid[0][1]}] [{grid[0][2]}]")
        print(f"[{grid[1][0]}] [{grid[1][1]}] [{grid[1][2]}]")
        print("H-shifter gate pattern - matches real shifter layout!")

    def print_rotated_gear_layout(self):
        """Print the gear screen layout adjusted for rotation"""
        layout = self.screen_layouts["gears"]
        
        # Create 3x2 grid based on rotated layout
        grid = [""] * 6
        
        for button_id, button_type in layout.items():
            gear_num = button_type.replace("gear", "")
            grid[button_id] = gear_num
        
        print("┌────────┬────────┬────────┐")
        print(f"│   {grid[0]}    │   {grid[1]}    │   {grid[2]}    │")
        print("│        │        │        │")
        print("├────────┼────────┼────────┤")
        print(f"│   {grid[3]}    │   {grid[4]}    │   {grid[5]}    │")
        print("│        │        │        │")
        print("└────────┴────────┴────────┘")
        if self.rotation != 0:
            print(f"   (Rotated {self.rotation}°)")
        
    def initialize_streamdeck(self):
        """Initialize Stream Deck connection"""
        if self.simulate or not STREAMDECK_AVAILABLE:
            logger.info("Running in simulation mode")
            print("🔄 Running in Stream Deck simulation mode")
            print("📱 Virtual Stream Deck Mini initialized (3x2 layout)")
            print(f"🔆 Virtual brightness set to {self.brightness}%")
            print(f"🔄 Virtual rotation set to {self.rotation}°")
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
            self.deck.set_brightness(self.brightness)
            
            # Set up button press callback
            self.deck.set_key_callback(self.button_callback)
            
            logger.info(f"Connected to {self.deck.deck_type()}")
            logger.info(f"Buttons: {self.deck.key_count()}")
            logger.info(f"Brightness set to {self.brightness}%")
            logger.info(f"Rotation set to {self.rotation}°")
            print(f"✅ Connected to {self.deck.deck_type()}")
            print(f"🔆 Brightness set to {self.brightness}%")
            print(f"🔄 Rotation set to {self.rotation}°")
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
        if text:
            text_bbox = draw.textbbox((0, 0), text, font=font_large)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (80 - text_width) // 2
            draw.text((text_x, 5), text, font=font_large, fill=color)
        
        # Draw value
        if value:
            value_bbox = draw.textbbox((0, 0), str(value), font=font_small)
            value_width = value_bbox[2] - value_bbox[0]
            value_x = (80 - value_width) // 2
            draw.text((value_x, 35), str(value), font=font_small, fill=color)
        
        # Draw progress bar
        if progress is not None:
            bar_width = 60
            bar_height = 8
            bar_x = (80 - bar_width) // 2
            bar_y = 60
            
            # Background bar
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(50, 50, 50))
            
            # Progress fill
            if progress > 0:
                fill_width = int((progress / 100) * bar_width)
                progress_color = (255, 0, 0) if progress > 90 else (0, 255, 0) if progress > 70 else (255, 255, 0)
                draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=progress_color)
        
        # Apply rotation if specified
        if self.rotation != 0:
            image = image.rotate(-self.rotation, expand=False)
        
        return image
    
    def create_initial_buttons(self):
        """Create initial button layout for current screen"""
        if self.current_screen == "main":
            self.create_main_screen()
        elif self.current_screen == "gears":
            self.create_gear_screen()
        elif self.current_screen == "h_shifter":
            self.create_h_shifter_screen()
    
    def create_main_screen(self):
        """Create the main telemetry screen"""
        if self.simulate:
            print("🔄 Initializing Main Screen...")
            self.print_rotated_main_layout()
            return
            
        buttons = {
            "shift": self.create_button_image("SHIFT", "Ready", color=(255, 255, 255)),
            "suggested": self.create_button_image("GT7", "N", color=(255, 255, 255)),
            "gear": self.create_button_image("GEAR", "N"),
            "speed": self.create_button_image("SPEED", "0 km/h"),
            "rpm": self.create_button_image("RPM", "0", progress=0),
            "status": self.create_button_image("STATUS", "Waiting", color=(255, 255, 0))
        }
        
        layout = self.screen_layouts[self.current_screen]
        for button_id, button_type in layout.items():
            if button_type in buttons:
                # Convert PIL image to Stream Deck format
                image = PILHelper.to_native_format(self.deck, buttons[button_type])
                self.deck.set_key_image(button_id, image)
    
    def create_gear_screen(self):
        """Create the gear visualization screen"""
        if self.simulate:
            print("🔄 Initializing Gear Screen...")
            self.print_rotated_gear_layout()
            return
            
        # Create gear buttons 1-6 (no text, just colors)
        for gear_num in range(1, 7):
            button_id = gear_num - 1  # buttons 0-5 for gears 1-6
            # Default to dark background
            image = self.create_button_image("", "", color=(80, 80, 80), bg_color=(20, 20, 20))
            
            if self.deck:
                native_image = PILHelper.to_native_format(self.deck, image)
                self.deck.set_key_image(button_id, native_image)

    def create_h_shifter_screen(self):
        """Create the H-shifter pattern screen"""
        if self.simulate:
            print("🔄 Initializing H-Shifter Screen...")
            self.print_rotated_h_shifter_layout()
            return
            
        # Create H-shifter buttons (no text, just colors)
        for button_id in range(6):
            # Default to dark background
            image = self.create_button_image("", "", color=(80, 80, 80), bg_color=(20, 20, 20))
            
            if self.deck:
                native_image = PILHelper.to_native_format(self.deck, image)
                self.deck.set_key_image(button_id, native_image)

    def update_h_shifter_screen_telemetry(self):
        """Update H-shifter screen with telemetry data"""
        global current_telemetry, shift_light_active
        
        if not current_telemetry:
            return
            
        if self.simulate:
            # In simulation mode, just print the layout once
            return
            
        # Get telemetry data
        gear = getattr(current_telemetry, 'current_gear', 0) 
        suggested_gear_num = getattr(current_telemetry, 'suggested_gear', 0)
        
        # Update each button based on the H-shifter layout
        for button_id in range(6):
            # Find which gear this button represents in the rotated H-shifter layout
            gear_button_name = None
            for bid, btype in self.screen_layouts["h_shifter"].items():
                if bid == button_id:
                    gear_button_name = btype
                    break
            
            if not gear_button_name:
                continue
                
            # Extract gear number from gear_button_name (e.g., "gear1" -> 1)
            gear_num = int(gear_button_name.replace("gear", ""))
            
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
            
            if self.deck:
                native_image = PILHelper.to_native_format(self.deck, image)
                self.deck.set_key_image(button_id, native_image)
    
    def button_callback(self, deck, key, state):
        """Handle button press events - any button press switches screens"""
        if state:  # Only handle button press (not release)
            self.switch_screen()
    
    def switch_screen(self):
        """Switch to the next screen"""
        screens = list(self.screen_layouts.keys())
        current_index = screens.index(self.current_screen)
        next_index = (current_index + 1) % len(screens)
        self.current_screen = screens[next_index]
        
        # Create user-friendly screen name
        screen_names = {
            "main": "Main Telemetry",
            "gears": "Sequential Gears", 
            "h_shifter": "H-Pattern Shifter"
        }
        screen_display_name = screen_names.get(self.current_screen, self.current_screen)
        print(f"🔄 Switching to {screen_display_name} screen")
        
        # Recreate the screen layout
        self.create_initial_buttons()
        
        # Update display if we have telemetry data
        if current_telemetry is not None:
            self.update_telemetry_display()
    
    def update_button(self, button_type, text, value="", color=(255, 255, 255), bg_color=(0, 0, 0), progress=None):
        """Update a specific button"""
        if self.simulate:
            return
            
        try:
            # Find button ID for this type in current screen layout
            button_id = None
            current_layout = self.screen_layouts.get(self.current_screen, {})
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
    
    def update_telemetry_display(self):
        """Update all buttons with current telemetry data"""
        global current_telemetry, shift_light_active, driving_mode_active
        
        if current_telemetry is None:
            return
            
        if self.current_screen == "main":
            self.update_main_screen_telemetry()
        elif self.current_screen == "gears":
            self.update_gear_screen_telemetry()
        elif self.current_screen == "h_shifter":
            self.update_h_shifter_screen_telemetry()
    
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
                # Find the correct button ID for this gear in the rotated layout
                gear_button_name = f"gear{gear_num}"
                button_id = None
                for bid, btype in self.screen_layouts["gears"].items():
                    if btype == gear_button_name:
                        button_id = bid
                        break
                
                if button_id is None:
                    continue
                
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
                    if gear_num == 1:
                        status = "🟢" if gear == gear_num else "🟠" if suggested_gear_num == gear_num else "⚫"
                        print(f"\rGears: {status}", end="")
                    elif gear_num <= 6:
                        status = "🟢" if gear == gear_num else "🟠" if suggested_gear_num == gear_num else "⚫"
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
        response = requests.get(
            f"{HA_URL}/api/states/{entity_id}",
            headers={'Authorization': f'Bearer {HA_TOKEN}'}
        )
        if response.status_code == 200:
            return response.json()['state']
        return None
    except Exception as e:
        logger.error(f"Error getting light state: {e}")
        return None

def set_light_brightness(entity_id, brightness):
    """Set light brightness (0.0-1.0)"""
    try:
        brightness_255 = int(brightness * 255)
        response = requests.post(
            f"{HA_URL}/api/services/light/turn_on",
            headers={'Authorization': f'Bearer {HA_TOKEN}'},
            json={
                'entity_id': entity_id,
                'brightness': brightness_255
            }
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error setting light brightness: {e}")
        return False

def turn_off_light(entity_id):
    """Turn off a light"""
    try:
        response = requests.post(
            f"{HA_URL}/api/services/light/turn_off",
            headers={'Authorization': f'Bearer {HA_TOKEN}'},
            json={'entity_id': entity_id}
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error turning off light: {e}")
        return False

def set_shift_light_brightness(brightness):
    """Set the shift light brightness with red color"""
    global last_light_state
    
    if brightness > 0:
        # Set red color for shift light
        try:
            brightness_255 = int(brightness * 255)
            response = requests.post(
                f"{HA_URL}/api/services/light/turn_on",
                headers={'Authorization': f'Bearer {HA_TOKEN}'},
                json={
                    'entity_id': HUE_LIGHT_ENTITY,
                    'brightness': brightness_255,
                    'rgb_color': [255, 0, 0]  # Red color
                }
            )
            success = response.status_code == 200
            if success:
                last_light_state = brightness
            return success
        except Exception as e:
            logger.error(f"Error setting shift light brightness: {e}")
            return False
    else:
        success = turn_off_light(HUE_LIGHT_ENTITY)
        if success:
            last_light_state = 0
        return success

def enter_driving_mode():
    """Enter driving mode - turn off room lights"""
    global driving_mode_active
    
    if driving_mode_active:
        return
    
    driving_mode_active = True
    logger.info("🏁 Entering driving mode - turning off room lights")
    
    for light_entity in ROOM_LIGHTS:
        turn_off_light(light_entity)

def exit_driving_mode():
    """Exit driving mode - turn on room lights and shift light"""
    global driving_mode_active, shift_light_active, telemetry_timer
    
    if not driving_mode_active:
        return
    
    driving_mode_active = False
    shift_light_active = False
    
    if telemetry_timer:
        telemetry_timer.cancel()
        telemetry_timer = None
    
    logger.info("🛑 Exiting driving mode - turning on room lights")
    
    # Turn on room lights
    for light_entity in ROOM_LIGHTS:
        set_light_brightness(light_entity, 1.0)
    
    # Turn off shift light
    turn_off_light(HUE_LIGHT_ENTITY)

def is_telemetry_data_changing(packet):
    """Check if telemetry data is actually changing (not frozen)"""
    global last_telemetry_data, data_frozen_start
    
    try:
        # Create a simple signature of the data
        current_data = (
            getattr(packet, 'engine_rpm', 0),
            getattr(packet, 'speed_kph', 0),
            getattr(packet, 'current_gear', 0),
            getattr(packet, 'throttle', 0),
            getattr(packet, 'brake', 0)
        )
        
        if last_telemetry_data != current_data:
            # Data changed
            last_telemetry_data = current_data
            data_frozen_start = None
            return True, 0
        else:
            # Data hasn't changed
            if data_frozen_start is None:
                data_frozen_start = time.time()
            
            frozen_duration = time.time() - data_frozen_start
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

def print_status(status):
    """Print status with carriage return to overwrite previous line"""
    global last_status
    
    if status != last_status:
        # Clear previous line and print new status
        print(f"\r{' ' * 60}\r{status}", end='', flush=True)
        last_status = status

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
            print_status("🏁 Racing - Room lights OFF")
            
            # Handle shift light
            at_rev_limit = getattr(telemetry, 'rev_limit', False)
            
            if at_rev_limit and not shift_light_active:
                logger.info("🔴 Shift light ON - Rev limit reached!")
                shift_light_active = True
                set_shift_light_brightness(1.0)
                print_status("🏁 Racing - Room lights OFF | 🔴 SHIFT!")
                
            elif not at_rev_limit and shift_light_active:
                logger.info("⚫ Shift light OFF - Rev limit cleared")
                shift_light_active = False
                set_shift_light_brightness(0.0)
                print_status("🏁 Racing - Room lights OFF")
        else:
            # Data frozen in driving context - exit immediately
            if frozen_duration > 1.0:  # Small delay to avoid flickering
                print_status("⏸️  Paused - Exiting driving mode...")
                exit_driving_mode()
                print_status("⏸️  Paused - Room lights ON")
    else:
        # Not in racing context
        print_status("⏳ Waiting for GT7 activity...")
        if data_changing or frozen_duration > 30.0:
            exit_driving_mode()

def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running, telemetry_timer, stream_deck_gt7, gt7_client
    
    print("\n🛑 Shutdown signal received...")
    logger.info("Shutdown signal received...")
    running = False
    
    # Stop GT7 client first to prevent new callbacks
    if gt7_client:
        try:
            logger.info("Stopping GT7 telemetry client...")
            gt7_client.stop()
        except Exception as e:
            logger.error(f"Error stopping GT7 client: {e}")
    
    if telemetry_timer:
        telemetry_timer.cancel()
    
    exit_driving_mode()
    
    if stream_deck_gt7:
        stream_deck_gt7.close()
    
    print("👋 Goodbye!")
    sys.exit(0)

def main():
    """Main function"""
    global running, stream_deck_gt7, gt7_client
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='GT7 Stream Deck Integration')
    parser.add_argument('--simulate', action='store_true', 
                       help='Run in simulation mode without hardware')
    parser.add_argument('--brightness', type=int, default=50, choices=range(1, 101),
                       help='Set Stream Deck brightness (1-100, default: 50)')
    parser.add_argument('--rotation', type=int, default=0, choices=[0, 90, 180, 270],
                       help='Rotate Stream Deck display (0, 90, 180, 270 degrees, default: 0)')
    args = parser.parse_args()
    
    logger.info("Starting GT7 Stream Deck integration")
    logger.info(f"Stream Deck brightness: {args.brightness}%")
    logger.info(f"Stream Deck rotation: {args.rotation}°")
    logger.info(f"Configured room lights: {ROOM_LIGHTS}")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Initialize Stream Deck
    stream_deck_gt7 = StreamDeckGT7(simulate=args.simulate, brightness=args.brightness, rotation=args.rotation)
    
    # Initialize Stream Deck
    if not stream_deck_gt7.initialize_streamdeck():
        logger.error("Failed to initialize Stream Deck")
        return
    
    try:
        # Start GT7 telemetry with standard client
        try:
            gt7_client = TurismoClient(ps_ip=PS5_IP)
            print("✅ Connected to PS5 successfully!")
        except PlayStatonOnStandbyError:
            print("❌ Error: PlayStation at {} is on standby.".format(PS5_IP))
            print("💡 Please turn on your PS5 manually and try again.")
            return
        except Exception as e:
            print(f"❌ Error connecting to PS5: {e}")
            return
            
        gt7_client.register_callback(telemetry_callback)
        
        telemetry_thread = threading.Thread(target=gt7_client.start, daemon=True)
        telemetry_thread.start()
        
        logger.info("GT7 telemetry client started")
        if args.simulate:
            logger.info("Stream Deck simulation mode running...")
            print("🎮 GT7 Stream Deck simulation running...")
            print("📊 Multi-screen support active - press any button to switch")
            print("🛑 Press Ctrl+C to stop")
        else:
            logger.info("Stream Deck GT7 dashboard running...")
            print("🎮 GT7 Stream Deck dashboard running...")
            print("📱 Multi-screen support active - press any button to switch")
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
        
        # Stop GT7 client first
        if gt7_client:
            try:
                logger.info("Stopping GT7 telemetry client...")
                gt7_client.stop()
            except Exception as e:
                logger.error(f"Error stopping GT7 client: {e}")
        
        if stream_deck_gt7:
            stream_deck_gt7.close()
        
        exit_driving_mode()

if __name__ == "__main__":
    main()
