#!/usr/bin/env python3
"""
Super Simple COM9 Test - Exact copy of working BGA_test.py logic
"""

import serial
import time

def send(ser, cmd):
    ser.write((cmd + '\r\n').encode('ascii'))
    time.sleep(0.1)
    return ser.read_all().decode('ascii', errors='ignore').strip()

print("🧪 Testing COM9 with EXACT same logic as working BGA_test.py...")

try:
    # Connect to BGA244 - EXACT same as BGA_test.py
    print("   → Opening COM9...")
    ser = serial.Serial('COM9', 9600, timeout=1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("   ✅ COM9 opened successfully")

    # Set mode and gases - EXACT same commands
    print("   → Setting mode and gases...")
    mode_resp = send(ser, "MSMD 1")                # Binary gas mode
    gas1_resp = send(ser, "GASP 7782-44-7")        # Primary gas: O2
    gas2_resp = send(ser, "GASS 7727-37-9")        # Secondary gas: N2

    print(f"   → MSMD 1: '{mode_resp}'")
    print(f"   → GASP: '{gas1_resp}'") 
    print(f"   → GASS: '{gas2_resp}'")

    # Read values - EXACT same as BGA_test.py
    print("   → Reading values...")
    temp = send(ser, "TCEL?")
    pressure = send(ser, "PRES?") 
    sos = send(ser, "NSOS?")
    primary_gas = send(ser, "RATO? 1")

    print("📊 RESULTS:")
    print("Temperature:", temp, "°C")
    print("Pressure:", pressure, "psi")
    print("Speed of Sound:", sos, "m/s") 
    print("Primary Gas Concentration:", primary_gas, "%")

    # Close connection - EXACT same
    ser.close()
    print("✅ COM9 test SUCCESSFUL!")

except Exception as e:
    print(f"❌ COM9 test FAILED: {e}")
    print(f"   Error type: {type(e).__name__}")
    
    try:
        ser.close()
    except:
        pass 