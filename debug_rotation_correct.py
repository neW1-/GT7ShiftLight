#!/usr/bin/env python3
"""Debug script to figure out correct rotation mapping using human-friendly numbering (1-6)"""

def print_layout(title, layout):
    """Print a visual representation of the 3x2 button layout"""
    print(f"\n{title}:")
    # Convert 0-based to 1-based for display
    display_layout = {}
    for button_0based, gear in layout.items():
        button_1based = button_0based + 1
        display_layout[button_1based] = gear
    
    # Print as 3x2 grid
    print(f"[{display_layout.get(1, '?')}] [{display_layout.get(2, '?')}] [{display_layout.get(3, '?')}]")
    print(f"[{display_layout.get(4, '?')}] [{display_layout.get(5, '?')}] [{display_layout.get(6, '?')}]")

# Original layout (0 degrees) - human friendly view
print("Original layout (0°) - human-friendly:")
print("[gear1] [gear2] [gear3]")
print("[gear4] [gear5] [gear6]")

# When rotated 90° clockwise, the physical buttons are:
# - Button 1 (top-left) becomes position of old button 4 (bottom-left) 
# - Button 2 (top-middle) becomes position of old button 1 (top-left)
# - Button 3 (top-right) becomes position of old button 2 (top-middle)
# - Button 4 (bottom-left) becomes position of old button 5 (bottom-middle)
# - Button 5 (bottom-middle) becomes position of old button 6 (bottom-right)  
# - Button 6 (bottom-right) becomes position of old button 3 (top-right)

print("\nAfter 90° clockwise rotation, we want:")
print("[gear4] [gear1]")
print("[gear5] [gear2]")  
print("[gear6] [gear3]")

print("\nSo the mapping should be:")
print("gear1 -> button 3 (was button 1)")
print("gear2 -> button 6 (was button 2)")  
print("gear3 -> button 9... wait, that's wrong")

print("\nLet me think differently...")
print("90° clockwise rotation means:")
print("- Top row [1,2,3] becomes right column [3,6]")
print("- Bottom row [4,5,6] becomes left column [1,4]")

print("\nSo:")
print("Original [1,2,3] -> New positions [4,1,2]")  
print("Original [4,5,6] -> New positions [5,6,3]")

print("\nTherefore:")
print("gear1 (was pos 1) -> pos 4")
print("gear2 (was pos 2) -> pos 1") 
print("gear3 (was pos 3) -> pos 2")
print("gear4 (was pos 4) -> pos 5")
print("gear5 (was pos 5) -> pos 6")
print("gear6 (was pos 6) -> pos 3")

print("\nIn 0-based indexing (for the code):")
print("gear1 (was pos 0) -> pos 3")
print("gear2 (was pos 1) -> pos 0") 
print("gear3 (was pos 2) -> pos 1")
print("gear4 (was pos 3) -> pos 4")
print("gear5 (was pos 4) -> pos 5")
print("gear6 (was pos 5) -> pos 2")

# So the rotation map should be:
rotation_map_90 = {0: 3, 1: 0, 2: 1, 3: 4, 4: 5, 5: 2}
print(f"\nCorrect rotation map for 90°: {rotation_map_90}")

# Test this mapping
original_gears = {0: "gear1", 1: "gear2", 2: "gear3", 3: "gear4", 4: "gear5", 5: "gear6"}
rotated_gears_90 = {rotation_map_90[k]: v for k, v in original_gears.items()}

print_layout("Original (0°)", original_gears)
print_layout("Rotated 90°", rotated_gears_90)
