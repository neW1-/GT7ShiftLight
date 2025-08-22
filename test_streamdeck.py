#!/usr/bin/env python3
"""
Test Stream Deck detection and basic functionality
"""

import sys
import os

try:
    from StreamDeck.DeviceManager import DeviceManager
    from StreamDeck.ImageHelpers import PILHelper
    from PIL import Image, ImageDraw, ImageFont
    print("✅ All Stream Deck libraries imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def main():
    print("🔍 Scanning for Stream Deck devices...")
    
    try:
        streamdecks = DeviceManager().enumerate()
        
        if not streamdecks:
            print("❌ No Stream Deck devices found")
            print("Make sure your Stream Deck is:")
            print("  - Connected via USB")
            print("  - Not being used by the official Stream Deck software")
            print("  - Not locked by another application")
            return False
        
        print(f"✅ Found {len(streamdecks)} Stream Deck device(s):")
        
        for i, deck in enumerate(streamdecks):
            try:
                deck.open()
                print(f"  Device {i+1}:")
                print(f"    Type: {deck.deck_type()}")
                print(f"    Serial: {deck.get_serial_number()}")
                print(f"    Firmware: {deck.get_firmware_version()}")
                print(f"    Buttons: {deck.key_count()}")
                print(f"    Resolution: {deck.key_image_format()}")
                
                # Test creating a simple image
                image = Image.new('RGB', (80, 80), (0, 100, 0))
                draw = ImageDraw.Draw(image)
                draw.text((10, 30), "TEST", fill=(255, 255, 255))
                
                # Convert to Stream Deck format
                native_image = PILHelper.to_native_format(deck, image)
                
                print(f"    ✅ Image conversion successful")
                print(f"    📱 Setting test image on button 0...")
                
                # Set the image on button 0
                deck.set_key_image(0, native_image)
                
                deck.close()
                
            except Exception as e:
                print(f"    ❌ Could not open device: {e}")
                print(f"    💡 Try running with: sudo python3 test_streamdeck.py")
                print(f"    💡 Or close the Stream Deck software if it's running")
                return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎉 Stream Deck test successful!")
        print("You can now run: python3 streamdeck_gt7.py")
    else:
        print("\n❌ Stream Deck test failed")
        print("Please check your Stream Deck connection and permissions")
