#!/usr/bin/env python3
"""
Minimal Ctrl+C test for Stream Deck script
Tests just the shutdown handling without GT7 telemetry
"""

import signal
import sys
import time
import threading
import argparse

running = True
stream_deck_gt7 = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    
    print("\n🛑 Shutdown signal received...")
    running = False
    print("👋 Goodbye!")
    sys.exit(0)

def mock_update():
    """Mock update function"""
    print(".", end="", flush=True)

def main():
    """Test main function"""
    global running
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Test Ctrl+C handling')
    parser.add_argument('--simulate', action='store_true', help='Simulate mode')
    args = parser.parse_args()
    
    print("🧪 Testing Ctrl+C handling...")
    print("🛑 Press Ctrl+C to stop (or wait 10 seconds for auto-stop)")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        start_time = time.time()
        loop_count = 0
        
        while running and (time.time() - start_time) < 10:  # Auto-stop after 10 seconds
            mock_update()
            
            # Check for shutdown more frequently
            for i in range(10):
                if not running:
                    break
                time.sleep(0.01)
            
            loop_count += 1
            if loop_count % 50 == 0:  # Every 5 seconds
                print(f"\n📊 Running for {time.time() - start_time:.1f}s...")
                
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt caught in main loop")
        running = False
    finally:
        print("\n🔄 Cleanup complete")
        running = False

if __name__ == "__main__":
    main()
