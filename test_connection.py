#!/usr/bin/env python3
import socket
import time
import yaml

# Load config
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    PS5_IP = config['ps5_ip']
except Exception as e:
    print(f"Error loading config: {e}")
    PS5_IP = "192.168.68.145"  # fallback

print(f"Testing connection to PS5 at {PS5_IP}")

# Test 1: Basic network connectivity
print("\n1. Testing basic ping connectivity...")
import subprocess
try:
    result = subprocess.run(['ping', '-c', '3', PS5_IP], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print("✅ Ping successful")
    else:
        print("❌ Ping failed")
        print(result.stderr)
except Exception as e:
    print(f"❌ Ping error: {e}")

# Test 2: Test UDP ports
print("\n2. Testing UDP ports...")
GT7_RECEIVE_PORT = 33339 + 400  # 33739 for GT7
GT7_BIND_PORT = 33340 + 400     # 33740 for GT7

print(f"Sending heartbeat to {PS5_IP}:{GT7_RECEIVE_PORT}")
try:
    # Send heartbeat message
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    message = b'A'  # Standard heartbeat
    sock.sendto(message, (PS5_IP, GT7_RECEIVE_PORT))
    print("✅ Heartbeat sent successfully")
    sock.close()
except Exception as e:
    print(f"❌ Failed to send heartbeat: {e}")

# Test 3: Try to listen for data
print(f"\n3. Listening on port {GT7_BIND_PORT} for 10 seconds...")
try:
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_sock.bind(('0.0.0.0', GT7_BIND_PORT))
    listen_sock.settimeout(10)
    
    # Send another heartbeat while listening
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(b'A', (PS5_IP, GT7_RECEIVE_PORT))
    send_sock.close()
    
    print("Waiting for data...")
    data, addr = listen_sock.recvfrom(4096)
    print(f"✅ Received {len(data)} bytes from {addr}")
    print(f"First 20 bytes: {data[:20]}")
    listen_sock.close()
    
except socket.timeout:
    print("❌ No data received (timeout)")
    listen_sock.close()
except Exception as e:
    print(f"❌ Listen error: {e}")

print("\n4. Checking GT7 requirements:")
print("- Is GT7 running on your PS5?")
print("- Are you in a race, time trial, or driving mode? (not menus)")
print("- Is your Pi on the same network as the PS5?")
print("- What app are you using on your phone that works?")
