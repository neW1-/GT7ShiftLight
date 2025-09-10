#!/usr/bin/env python3
"""Simple test to show the three screen layouts"""

def show_h_shifter_layout():
    """Show the H-shifter button layout"""
    print("=== H-SHIFTER SCREEN LAYOUT (No Rotation) ===")
    print()
    print("Button Layout:")
    print("[1] [2] [3]")
    print("[4] [5] [6]")
    print()
    print("Gear Mapping (H-shifter gate pattern):")
    print("[G1] [G3] [G5]  <- Top row")
    print("[G2] [G4] [G6]  <- Bottom row")
    print()
    print("This matches the real H-shifter gate pattern!")
    print("- Left column: 1st and 2nd gear")  
    print("- Middle column: 3rd and 4th gear")
    print("- Right column: 5th and 6th gear")
    print()

def show_sequential_layout():
    """Show the sequential gear layout"""
    print("=== SEQUENTIAL GEARS SCREEN LAYOUT (No Rotation) ===")
    print()
    print("Button Layout:")
    print("[1] [2] [3]")
    print("[4] [5] [6]")
    print()
    print("Gear Mapping (sequential order):")
    print("[G1] [G2] [G3]  <- Top row")
    print("[G4] [G5] [G6]  <- Bottom row")
    print()
    print("Perfect for paddle shifters and sequential transmissions!")
    print()

def show_main_layout():
    """Show the main telemetry layout"""
    print("=== MAIN TELEMETRY SCREEN LAYOUT (No Rotation) ===")
    print()
    print("Button Layout:")
    print("[1] [2] [3]")
    print("[4] [5] [6]")
    print()
    print("Telemetry Mapping:")
    print("[SHIFT] [GT7] [GEAR]  <- Top row")
    print("[SPEED] [RPM] [STATUS]  <- Bottom row")
    print()
    print("Complete racing telemetry at a glance!")
    print()

if __name__ == "__main__":
    print("🏁 GT7 Stream Deck - Three Screen Layouts 🏁")
    print()
    show_main_layout()
    show_sequential_layout() 
    show_h_shifter_layout()
    print("🔄 Press any Stream Deck button to cycle between screens during gameplay!")
    print("📈 All three screens support rotation (0°, 90°, 180°, 270°) with automatic layout adjustment!")
