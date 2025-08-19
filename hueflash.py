import os
import time
import requests
import logging
from gt_telem.turismo_client import TurismoClient

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

def set_light_brightness(brightness):
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
        logger.error(f"Failed to turn on light: {e}")

def turn_off_light():
    url = f"{HA_URL}/api/services/light/turn_off"
    data = {"entity_id": HUE_LIGHT_ENTITY}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to turn off light: {e}")

# Global variable to track shift state
shift_light_active = False

def telemetry_callback(packet):
    global shift_light_active
    
    # Use GT7's built-in rev limit flag (it's called 'rev_limit', not 'on_rev_limit')
    at_rev_limit = getattr(packet, 'rev_limit', False)
    
    # Turn on shift light when rev limit is reached
    if at_rev_limit and not shift_light_active:
        logger.info("Shift light ON - Rev limit reached!")
        shift_light_active = True
        set_light_brightness(1.0)
        
    # Turn off shift light when rev limit is cleared
    elif not at_rev_limit and shift_light_active:
        logger.info("Shift light OFF - Rev limit cleared")
        shift_light_active = False
        turn_off_light()

def main():
    logger.info("Starting GT7 Hue Shift Light (Rev Limit Mode)")
    
    try:
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(telemetry_callback)
        client.start()
        
        logger.info("Connected to GT7. Shift light ready!")
        while True:
            time.sleep(10)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if 'client' in locals():
            client.stop()
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()
