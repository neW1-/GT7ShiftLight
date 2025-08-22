#!/usr/bin/env python3
"""Debug script to show gear button mappings for different rotations"""

def setup_rotated_layouts(rotation):
    """Create button layouts adjusted for rotation"""
    # Original layouts (0 degrees)
    original_gears = {
        0: "gear1",        # Top left
        1: "gear2",        # Top middle
        2: "gear3",        # Top right
        3: "gear4",        # Bottom left
        4: "gear5",        # Bottom middle
        5: "gear6"         # Bottom right
    }
    
    # Apply rotation mapping
    if rotation == 0:
        rotated_gears = original_gears
    elif rotation == 90:  # 90° clockwise
        # Button mapping for 90° rotation: [0,1,2] -> [1,2,5]
        #                                   [3,4,5] -> [0,3,4]
        rotation_map = {0: 1, 1: 2, 2: 5, 3: 0, 4: 3, 5: 4}
        rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
    elif rotation == 180:  # 180° rotation
        # Button mapping for 180° rotation: [0,1,2] -> [5,4,3]
        #                                    [3,4,5] -> [2,1,0]
        rotation_map = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0}
        rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
    elif rotation == 270:  # 270° clockwise (90° counter-clockwise)
        # Button mapping for 270° rotation: [0,1,2] -> [3,0,1]
        #                                    [3,4,5] -> [4,5,2]
        rotation_map = {0: 3, 1: 0, 2: 1, 3: 4, 4: 5, 5: 2}
        rotated_gears = {rotation_map[k]: v for k, v in original_gears.items()}
    
    return rotated_gears

def test_gear_lookup(rotation, gear_num):
    """Test which button ID a gear maps to"""
    rotated_gears = setup_rotated_layouts(rotation)
    gear_button_name = f"gear{gear_num}"
    
    button_id = None
    for bid, btype in rotated_gears.items():
        if btype == gear_button_name:
            button_id = bid
            break
    
    return button_id

# Test different rotations
for rotation in [0, 90, 180, 270]:
    print(f"\n--- Rotation {rotation}° ---")
    rotated_layout = setup_rotated_layouts(rotation)
    print("Button layout:", rotated_layout)
    
    print("Gear to button mapping:")
    for gear_num in range(1, 7):
        button_id = test_gear_lookup(rotation, gear_num)
        print(f"  gear{gear_num} -> button {button_id}")
