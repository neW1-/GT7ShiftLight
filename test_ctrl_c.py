#!/usr/bin/env python3
"""
Test Ctrl+C handling for GT7 Stream Deck script
"""

import signal
import sys
import time
import subprocess
import os

def test_ctrl_c():
    """Test that Ctrl+C properly shuts down the Stream Deck script"""
    print("🧪 Testing Ctrl+C handling for streamdeck_gt7.py...")
    
    script_path = "/Users/martin/Documents/dev/gt7/hueflash/streamdeck_gt7.py"
    venv_python = "/Users/martin/Documents/dev/gt7/.venv/bin/python"
    
    try:
        # Start the process
        print("▶️  Starting streamdeck_gt7.py --simulate...")
        process = subprocess.Popen(
            [venv_python, script_path, "--simulate"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/Users/martin/Documents/dev/gt7/hueflash"
        )
        
        # Let it run for a moment
        time.sleep(2)
        
        # Send SIGINT (Ctrl+C)
        print("🛑 Sending Ctrl+C (SIGINT)...")
        process.send_signal(signal.SIGINT)
        
        # Wait for it to terminate
        try:
            stdout, stderr = process.communicate(timeout=5)
            print(f"✅ Process terminated with return code: {process.returncode}")
            
            if "Ctrl+C detected" in stdout or "Shutdown signal received" in stdout:
                print("✅ Ctrl+C handling message found in output")
            else:
                print("⚠️  No specific Ctrl+C message found, but process terminated")
                
            if process.returncode == 0:
                print("✅ Clean shutdown (return code 0)")
            elif process.returncode == 1:
                print("✅ Shutdown with expected error (return code 1)")
            else:
                print(f"⚠️  Unexpected return code: {process.returncode}")
                
        except subprocess.TimeoutExpired:
            print("❌ Process didn't terminate within 5 seconds, killing...")
            process.kill()
            return False
            
        # Show last few lines of output
        if stdout:
            lines = stdout.strip().split('\n')
            print("\n📝 Last few lines of output:")
            for line in lines[-5:]:
                print(f"   {line}")
                
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    if test_ctrl_c():
        print("\n🎉 Ctrl+C handling test PASSED!")
    else:
        print("\n❌ Ctrl+C handling test FAILED!")
        sys.exit(1)
