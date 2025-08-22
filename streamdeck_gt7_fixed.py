#!/usr/bin/env python3
"""
GT7 Stream Deck Mini Integration - Multi-Screen with PS5 Wake-up
==============================================================

This is a copy of streamdeck_gt7.py with added PS5 wake-up functionality.
When PS5 is in standby, it will attempt to wake it up automatically.

Usage: 
    python3 streamdeck_gt7_fixed.py --simulate
"""

import os
import subprocess
import socket
import time

# Copy your existing streamdeck_gt7.py imports and code here
# Then add this PS5 wake-up wrapper:

def wake_ps5(ps5_ip):
    """Wake up PS5 using network discovery packets"""
    try:
        print(f"🔄 Attempting to wake PS5 at {ps5_ip}...")
        
        # Send discovery packets that might wake the PS5
        wake_ports = [9302, 9303, 9304]
        
        for port in wake_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                wake_packet = b"WAKE * HTTP/1.1\ndevice-discovery-protocol-version:00030010"
                sock.sendto(wake_packet, (ps5_ip, port))
                sock.close()
                print(f"📡 Sent wake packet to {ps5_ip}:{port}")
            except Exception as e:
                print(f"Failed to send to port {port}: {e}")
        
        # Wait and test connection
        print("⏳ Waiting 5 seconds for PS5 to wake up...")
        time.sleep(5)
        
        # Test if PS5 is responding
        ping_result = subprocess.run(['ping', '-c', '1', '-W', '2000', ps5_ip], 
                                   capture_output=True, text=True)
        
        if ping_result.returncode == 0:
            print("✅ PS5 wake-up successful!")
            return True
        else:
            print("⚠️  PS5 may not have responded to wake-up attempt")
            print("💡 Make sure 'Enable turning on PS5 from network' is enabled in PS5 settings")
            return False
            
    except Exception as e:
        print(f"❌ Failed to wake PS5: {e}")
        return False

# To use this, wrap your TurismoClient creation like this:

def create_turismo_client_with_wake(ps5_ip, max_retries=2):
    """Create TurismoClient with automatic PS5 wake-up on standby"""
    from gt_telem.turismo_client import TurismoClient
    from gt_telem.errors.playstation_errors import PlayStatonOnStandbyError
    
    for attempt in range(max_retries):
        try:
            client = TurismoClient(ps_ip=ps5_ip)
            print("✅ Connected to PS5 successfully!")
            return client
            
        except PlayStatonOnStandbyError as e:
            print(f"❌ PS5 is in standby mode (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:  # Don't wake on last attempt
                if wake_ps5(ps5_ip):
                    print("🔄 Retrying connection after wake-up...")
                    time.sleep(2)
                    continue
                else:
                    print("❌ Failed to wake PS5, trying once more...")
            else:
                print("❌ Max retries reached. Please manually turn on your PS5.")
                raise e
                
        except Exception as e:
            print(f"❌ Other error connecting to PS5: {e}")
            raise e
    
    return None

if __name__ == "__main__":
    # Example usage
    PS5_IP = "192.168.68.145"  # Replace with your PS5 IP
    
    try:
        client = create_turismo_client_with_wake(PS5_IP)
        print("🎮 GT7 telemetry client ready!")
        # Continue with your existing streamdeck_gt7.py logic here...
        
    except Exception as e:
        print(f"Failed to connect: {e}")
