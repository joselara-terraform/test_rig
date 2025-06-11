#!/usr/bin/env python3
"""
BGA 1 Specific Debug Script
Focused debugging for BGA 1 on COM8 that's not returning measurements
"""

import serial
import time

def send_with_detailed_debug(ser, cmd, description=""):
    """Send command with very detailed debugging"""
    print(f"\n🔍 Testing: {cmd} {description}")
    print(f"   → Port status: {'Open' if ser.is_open else 'Closed'}")
    print(f"   → In waiting: {ser.in_waiting} bytes")
    
    # Clear any existing data
    if ser.in_waiting > 0:
        old_data = ser.read_all()
        print(f"   → Cleared {len(old_data)} bytes: {repr(old_data)}")
    
    # Send command
    command_bytes = (cmd + '\r\n').encode('ascii')
    print(f"   → Sending: {repr(command_bytes)}")
    bytes_written = ser.write(command_bytes)
    print(f"   → Bytes written: {bytes_written}")
    
    # Force send
    ser.flush()
    print(f"   → Data flushed to device")
    
    # Wait and check for data
    for i in range(5):  # Check 5 times over 1 second
        time.sleep(0.2)
        waiting = ser.in_waiting
        print(f"   → After {0.2*(i+1)}s: {waiting} bytes waiting")
        if waiting > 0:
            break
    
    # Read response
    response_bytes = ser.read_all()
    response = response_bytes.decode('ascii', errors='ignore').strip()
    
    print(f"   ← Raw bytes: {repr(response_bytes)} ({len(response_bytes)} total)")
    print(f"   ← Decoded text: '{response}'")
    print(f"   ← Length: {len(response)} characters")
    
    if response:
        print(f"   ✅ Got response: '{response}'")
    else:
        print(f"   ❌ No response received")
        
        # Try different approaches
        print(f"   🔧 Trying longer timeout...")
        time.sleep(0.5)
        late_response = ser.read_all()
        if late_response:
            late_text = late_response.decode('ascii', errors='ignore').strip()
            print(f"   ⏰ Late response: '{late_text}'")
            response = late_text
    
    return response

def main():
    """Debug BGA 1 specifically"""
    print("🔬 BGA 1 (COM8) Specific Debug Test")
    print("=" * 50)
    
    try:
        print("\n🔌 Opening COM8...")
        ser = serial.Serial(
            port="COM8",
            baudrate=9600,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=2
        )
        
        print(f"✅ COM8 opened successfully")
        print(f"   → Baudrate: {ser.baudrate}")
        print(f"   → Bytesize: {ser.bytesize}")  
        print(f"   → Stopbits: {ser.stopbits}")
        print(f"   → Parity: {ser.parity}")
        print(f"   → Timeout: {ser.timeout}")
        
        # Wait for device
        print(f"\n⏳ Waiting 2 seconds for device to be ready...")
        time.sleep(2)
        
        # Check initial state
        print(f"\n📊 Initial port state:")
        print(f"   → Bytes waiting: {ser.in_waiting}")
        if ser.in_waiting > 0:
            initial_data = ser.read_all()
            print(f"   → Initial data: {repr(initial_data)}")
        
        # Test sequence
        print(f"\n🧪 Testing Command Sequence:")
        
        # 1. Device identification
        idn = send_with_detailed_debug(ser, "*IDN?", "(Device identification)")
        
        # 2. Try alternative identification
        if not idn:
            print(f"\n🔄 Trying alternative identification commands...")
            send_with_detailed_debug(ser, "VER?", "(Version)")
            send_with_detailed_debug(ser, "ID?", "(ID)")
            send_with_detailed_debug(ser, "WHO?", "(Who)")
            send_with_detailed_debug(ser, "HELP", "(Help)")
        
        # 3. Mode setting
        send_with_detailed_debug(ser, "MSMD 1", "(Set binary mode)")
        
        # 4. Gas configuration  
        send_with_detailed_debug(ser, "GASP 7782-44-7", "(Primary gas: O2)")
        send_with_detailed_debug(ser, "GASS 1333-74-0", "(Secondary gas: H2)")
        
        # 5. Measurements
        print(f"\n📏 Testing measurement commands:")
        temp = send_with_detailed_debug(ser, "TCEL?", "(Temperature)")
        pres = send_with_detailed_debug(ser, "PRES?", "(Pressure)")  
        sos = send_with_detailed_debug(ser, "NSOS?", "(Speed of sound)")
        ratio1 = send_with_detailed_debug(ser, "RATO? 1", "(Primary gas ratio)")
        ratio2 = send_with_detailed_debug(ser, "RATO? 2", "(Secondary gas ratio)")
        
        # Summary
        print(f"\n📋 SUMMARY FOR BGA 1 (COM8):")
        print(f"   • Device ID: '{idn}'")
        print(f"   • Temperature: '{temp}'")
        print(f"   • Pressure: '{pres}'")
        print(f"   • Speed of Sound: '{sos}'")
        print(f"   • Primary Gas %: '{ratio1}'")
        print(f"   • Secondary Gas %: '{ratio2}'")
        
        responses = [idn, temp, pres, sos, ratio1, ratio2]
        valid_responses = [r for r in responses if r and r.strip()]
        
        if valid_responses:
            print(f"\n✅ BGA 1 is responding! Got {len(valid_responses)}/6 valid responses")
        else:
            print(f"\n❌ BGA 1 is not responding to any commands")
            print(f"   This suggests:")
            print(f"   • Wrong device type on COM8")
            print(f"   • Device not compatible with BGA244 protocol")
            print(f"   • Hardware/wiring issue")
            print(f"   • Device in wrong mode or needs initialization")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print(f"\n🏁 BGA 1 Debug Complete")

if __name__ == "__main__":
    main() 