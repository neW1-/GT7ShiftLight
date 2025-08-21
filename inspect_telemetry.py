#!/usr/bin/env python3
"""Quick script to inspect GT7 telemetry attributes"""

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

def inspect_telemetry(telemetry):
    """Print all available attributes in the telemetry object"""
    print("\n=== GT7 Telemetry Attributes ===")
    
    # Get all attributes
    attrs = [attr for attr in dir(telemetry) if not attr.startswith('_')]
    
    for attr in sorted(attrs):
        try:
            value = getattr(telemetry, attr)
            # Only show data attributes (not methods)
            if not callable(value):
                print(f"{attr}: {value}")
        except:
            pass
    
    print("=" * 40)
    
    # Stop after first packet
    import sys
    sys.exit(0)

def main():
    print("Connecting to GT7 to inspect telemetry data...")
    print(f"PS5 IP: {PS5_IP}")
    
    try:
        client = TurismoClient(ps_ip=PS5_IP)
        client.register_callback(inspect_telemetry)
        client.start()
        
        print("Waiting for telemetry data...")
        time.sleep(10)  # Wait for data
        
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
