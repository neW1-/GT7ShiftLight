#!/usr/bin/env python3
"""
GT7 Stream Deck PS5 Wake-up Test
================================

Test script to demonstrate PS5 wake-up functionality
"""

import socket
import subprocess
import time

def wake_ps5(ps5_ip):
    """
    Wake up PS5 using network discovery packets
    Note: PS5 must have 'Enable turning on PS5 from network' enabled in settings
    """
    try:
        print(f"🔄 Attempting to wake PS5 at {ps5_ip}...")
        
        # Try to ping the PS5 first to see if it wakes up from that
        ping_result = subprocess.run(['ping', '-c', '1', '-W', '1000', ps5_ip], 
                                   capture_output=True, text=True)
        
        if ping_result.returncode == 0:
            print("✅ PS5 appears to be responding to ping")
            return True
            
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
                print(f"Failed to send wake packet to port {port}: {e}")
        
        # Wait a moment and try ping again
        print("⏳ Waiting 5 seconds for PS5 to wake up...")
        time.sleep(5)
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

if __name__ == "__main__":
    # Test PS5 wake-up
    PS5_IP = "192.168.68.145"  # Your PS5 IP
    
    print("🎮 GT7 PS5 Wake-up Test")
    print(f"🔍 Testing PS5 at {PS5_IP}")
    
    # Test the wake-up functionality
    success = wake_ps5(PS5_IP)
    
    if success:
        print("🎉 PS5 Wake-up test completed successfully!")
        print("📱 Your Stream Deck script will now automatically wake the PS5 when needed")
    else:
        print("⚠️  PS5 Wake-up test completed with warnings")
        print("🔧 Check your PS5 network settings if wake-up didn't work")
