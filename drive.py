import os
import time
import requests
import logging
from gt_telem.turismo_client import TurismoClient
from threading import Timer

# Set up minimal logging
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
    global hue_light_state, room_light_state, data_frozen_start, last_telemetry_data, telemetry_timer, packet_count, shift_light_active
    packet_count += 1
    
    # Check if we're in a race context (not menus)
    in_race_context = is_actually_driving(telemetry)
    
    # Check if telemetry data is changing or frozen
    data_changing, frozen_duration = is_telemetry_data_changing(telemetry)
    
    # Debug logging every 60 packets (about once per second)
    if packet_count % 60 == 0:
        rpm = getattr(telemetry, 'engine_rpm', 0)
        speed = getattr(telemetry, 'speed_kph', 0)
        gear = getattr(telemetry, 'current_gear', 0)
        logger.info(f"🔍 Debug - In Race: {in_race_context}, Data Changing: {data_changing}, Frozen: {frozen_duration:.1f}s, RPM: {rpm:.0f}, Speed: {speed:.1f}kph, Gear: {gear}")
    
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

def main():
    logger.info("Starting GT7 Drive Mode with Room Lighting")
    logger.info(f"Configured room lights: {ROOM_LIGHTS}")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    logger.info(f"Telemetry timeout: {TELEMETRY_TIMEOUT} seconds")
    
    try:
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        client.start()
        
        logger.info("Connected to GT7. Waiting for driving activity...")
        while True:
            time.sleep(10)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        
        # Clean shutdown
        global telemetry_timer
        if telemetry_timer:
            telemetry_timer.cancel()
        
        exit_driving_mode()  # Restore room lights
        
        if 'client' in locals():
            client.stop()
        
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()