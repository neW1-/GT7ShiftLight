import os
import time
import requests
import logging
from gt_telem.turismo_client import TurismoClient

# Set up logging with more detail
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
except Exception:
    HA_TOKEN = os.getenv('HA_TOKEN')
    HUE_LIGHT_ENTITY = os.getenv('HUE_LIGHT_ENTITY')
    HA_URL = os.getenv('HA_URL')
    PS5_IP = os.getenv('PS5_IP')

if not all([HA_TOKEN, HUE_LIGHT_ENTITY, HA_URL, PS5_IP]):
    raise RuntimeError('Missing Home Assistant or PS5 config values')

headers = {
    'Authorization': f'Bearer {HA_TOKEN}',
    'Content-Type': 'application/json',
}

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

# Global variables
shift_light_active = False
packet_count = 0

def telemetry_callback(packet):
    global shift_light_active, packet_count
    packet_count += 1
    
    # Log detailed telemetry data every 60 packets (about once per second)
    if packet_count % 60 == 0:
        try:
            # Let's see what attributes are actually available
            logger.info(f"🔍 Available attributes: {dir(packet)}")
            
            # Try common attribute names
            speed = getattr(packet, 'speed', getattr(packet, 'car_speed', 'N/A'))
            rpm = getattr(packet, 'rpm', getattr(packet, 'current_rpm', 'N/A'))
            rev_limit = getattr(packet, 'rev_limit', getattr(packet, 'on_rev_limit', 'N/A'))
            gear = getattr(packet, 'gear', getattr(packet, 'current_gear', 'N/A'))
            
            logger.info(f"📊 Telemetry - RPM: {rpm}, Speed: {speed}, Gear: {gear}, Rev_Limit: {rev_limit}")
            
        except Exception as e:
            logger.error(f"Error logging telemetry: {e}")
    
    # Always handle shift light logic regardless of driving state (for testing)
    try:
        at_rev_limit = getattr(packet, 'rev_limit', getattr(packet, 'on_rev_limit', False))
        
        if at_rev_limit and not shift_light_active:
            logger.info("🔴 Shift light ON - Rev limit reached!")
            shift_light_active = True
            set_shift_light_brightness(1.0)
            
        elif not at_rev_limit and shift_light_active:
            logger.info("⚫ Shift light OFF - Rev limit cleared")
            shift_light_active = False
            turn_off_shift_light()
            
    except Exception as e:
        logger.error(f"Error in shift light logic: {e}")

def main():
    logger.info("Starting GT7 DEBUG MODE - Testing telemetry and shift light")
    logger.info(f"Shift light entity: {HUE_LIGHT_ENTITY}")
    
    try:
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        client.start()
        
        logger.info("Connected to GT7. Monitoring telemetry...")
        logger.info("This debug version will show detailed telemetry data and always respond to rev limit")
        
        while True:
            time.sleep(10)
            logger.info(f"Packets received: {packet_count}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if 'client' in locals():
            client.stop()
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()
