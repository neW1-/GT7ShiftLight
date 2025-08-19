#!/usr/bin/env python3
import socket
import time
import threading
import yaml

# Load config
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    PS5_IP = config['ps5_ip']
except Exception as e:
    print(f"Error loading config: {e}")
    PS5_IP = "192.168.68.145"

GT7_RECEIVE_PORT = 33339 + 400  # 33739 for GT7
GT7_BIND_PORT = 33340 + 400     # 33740 for GT7

print(f"GT7 Telemetry Test - PS5 at {PS5_IP}")
print(f"Sending to port {GT7_RECEIVE_PORT}, listening on {GT7_BIND_PORT}")
print("\nIMPORTANT: Make sure GT7 is running and you're actively driving!")
print("(In a race, time trial, or practice - not in menus)\n")

# Global flag to control heartbeat
keep_sending = True

def send_heartbeats():
    """Send continuous heartbeats every 10 seconds"""
    global keep_sending
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = b'A'
    
    while keep_sending:
        try:
            sock.sendto(message, (PS5_IP, GT7_RECEIVE_PORT))
            print(f"💓 Heartbeat sent at {time.strftime('%H:%M:%S')}")
            time.sleep(10)
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            break
    
    sock.close()

def listen_for_data():
    """Listen for telemetry data"""
    global keep_sending
    
    try:
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_sock.bind(('0.0.0.0', GT7_BIND_PORT))
        listen_sock.settimeout(1)  # Short timeout for responsive checking
        
        print("👂 Listening for telemetry data...")
        print("Press Ctrl+C to stop\n")
        
        packet_count = 0
        
        while keep_sending:
            try:
                data, addr = listen_sock.recvfrom(4096)
                packet_count += 1
                print(f"✅ Packet #{packet_count}: Received {len(data)} bytes from {addr}")
                
                if packet_count == 1:
                    print(f"First 50 bytes: {data[:50]}")
                    # Try to decode header
                    if len(data) >= 4:
                        header = data[:4]
                        print(f"Header: {header}")
                        
                elif packet_count % 60 == 0:  # Every 60 packets (about 1 second at 60Hz)
                    print(f"📊 Still receiving data... (packet #{packet_count})")
                    
            except socket.timeout:
                continue  # Normal timeout, keep checking
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Listen error: {e}")
    finally:
        listen_sock.close()

# Start heartbeat thread
heartbeat_thread = threading.Thread(target=send_heartbeats, daemon=True)
heartbeat_thread.start()

try:
    listen_for_data()
except KeyboardInterrupt:
    pass
finally:
    keep_sending = False
    print("\n🛑 Stopping...")

print("\nIf you got no data:")
print("1. Make sure GT7 is running and you're actively driving")
print("2. Check your phone app - what's it called?")
print("3. Some GT7 versions might need different ports or setup")
print("4. Try starting a race or time trial in GT7")
