#!/usr/bin/env python3
"""
Detailed OneWire Bit-by-Bit Analysis
"""

def analyze_onewire_detailed():
    """Analyze the first few sequences bit by bit to understand the protocol"""
    
    # Read the raw data
    with open('/home/pjakobs/devel/Boat_Temp/oneWire.txt', 'r') as f:
        lines = f.readlines()
    
    transitions = []
    data_started = False
    for line in lines:
        line = line.strip()
        if line.startswith(';') or not line:
            continue
        if line == 'microseconds,logic':
            data_started = True
            continue
        if data_started:
            parts = line.split(',')
            if len(parts) == 2:
                try:
                    time_us = int(parts[0])
                    logic_level = int(parts[1])
                    transitions.append((time_us, logic_level))
                except ValueError:
                    continue
    
    print("=== Detailed OneWire Analysis ===")
    
    # Look at the first sequence after the first reset/presence
    # Reset ends at ~486μs, presence around 513-622μs, data starts around 900μs
    
    print("\nAnalyzing first data sequence (900-3000μs):")
    
    # Find data slots in this range
    slots = []
    i = 0
    while i < len(transitions) - 1 and transitions[i][0] < 3000:
        time_us, level = transitions[i]
        
        if time_us < 900:  # Skip to data section
            i += 1
            continue
            
        # Look for falling edge (start of slot)
        if level == 0 and i > 0 and transitions[i-1][1] == 1:
            # Find rising edge (end of slot)
            slot_start = time_us
            j = i + 1
            while j < len(transitions):
                next_time, next_level = transitions[j]
                if next_level == 1:  # Rising edge found
                    slot_duration = next_time - slot_start
                    
                    # Look for inter-slot gap
                    recovery_start = next_time
                    recovery_end = None
                    if j + 1 < len(transitions):
                        recovery_end = transitions[j + 1][0]
                        recovery_duration = recovery_end - recovery_start if recovery_end else 0
                    else:
                        recovery_duration = 0
                    
                    slots.append({
                        'start': slot_start,
                        'end': next_time,
                        'duration': slot_duration,
                        'recovery': recovery_duration
                    })
                    
                    i = j
                    break
                j += 1
            else:
                i += 1
        else:
            i += 1
    
    print(f"Found {len(slots)} slots:")
    
    # Analyze each slot
    for i, slot in enumerate(slots[:64]):  # First 64 slots (8 bytes)
        duration = slot['duration']
        recovery = slot['recovery']
        
        # Determine bit value
        # OneWire read timing: Master pulls low 1-15μs, then releases
        # Device response: 
        # - For bit 1: device lets line go high quickly (total ~15μs)
        # - For bit 0: device keeps line low for ~60μs total
        
        if duration <= 20:
            bit_val = 1
            bit_type = "1 (short)"
        elif duration <= 70:
            bit_val = 0
            bit_type = "0 (medium)"  
        else:
            bit_val = 0
            bit_type = "0 (long)"
            
        byte_pos = i // 8
        bit_pos = i % 8
        
        print(f"  Slot {i:2d} (byte {byte_pos}, bit {bit_pos}): {duration:3d}μs low, {recovery:3d}μs high → {bit_type}")
        
        # Print byte summary every 8 bits
        if (i + 1) % 8 == 0:
            # Calculate byte value (LSB first)
            byte_bits = []
            byte_val = 0
            for j in range(8):
                slot_idx = i - 7 + j
                if slot_idx < len(slots):
                    dur = slots[slot_idx]['duration']
                    bit = 1 if dur <= 20 else 0
                    byte_bits.append(str(bit))
                    byte_val |= (bit << j)
            
            print(f"    → Byte {byte_pos}: {''.join(byte_bits)} = 0x{byte_val:02X} ({byte_val})")
    
    # Try to identify command structure
    print("\n=== Command Structure Analysis ===")
    if len(slots) >= 16:  # At least 2 bytes
        # Get first few bytes
        bytes_data = []
        for byte_idx in range(min(4, len(slots) // 8)):
            byte_val = 0
            for bit_idx in range(8):
                slot_idx = byte_idx * 8 + bit_idx
                if slot_idx < len(slots):
                    duration = slots[slot_idx]['duration']
                    bit = 1 if duration <= 20 else 0
                    byte_val |= (bit << bit_idx)
            bytes_data.append(byte_val)
        
        print("First few bytes:", [f"0x{b:02X}" for b in bytes_data])
        
        # Try to interpret
        if len(bytes_data) >= 1:
            cmd = bytes_data[0]
            if cmd == 0xCC:
                print("Command: SKIP ROM (0xCC)")
            elif cmd == 0x55:
                print("Command: MATCH ROM (0x55)")
            elif cmd == 0xBE:
                print("Command: READ SCRATCHPAD (0xBE)")
            elif cmd == 0x44:
                print("Command: CONVERT T (0x44)")
            else:
                print(f"Unknown command: 0x{cmd:02X}")

if __name__ == "__main__":
    analyze_onewire_detailed()