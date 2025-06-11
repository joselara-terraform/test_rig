#!/usr/bin/env python3
"""
BGA Debug Test Script
Comprehensive testing for all three BGA244 units to identify communication issues
"""

import serial
import time
import platform

def send_with_debug(ser, cmd, description=""):
    """Send command with detailed debugging output"""
    print(f"  → Sending: {cmd} {description}")
    
    # Clear buffers before sending
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Send command
    command_bytes = (cmd + '\r\n').encode('ascii')
    print(f"    Bytes sent: {repr(command_bytes)}")
    ser.write(command_bytes)
    
    # Wait for response
    time.sleep(0.2)  # Increased wait time
    
    # Read response
    response_bytes = ser.read_all()
    response = response_bytes.decode('ascii', errors='ignore').strip()
    
    print(f"    Raw response: {repr(response_bytes)} ({len(response_bytes)} bytes)")
    print(f"    Decoded: '{response}'")
    
    if not response:
        print(f"    ❌ No response to {cmd}")
    
    return response

def test_bga_port(port_name, bga_name):
    """Test a specific BGA on a specific port"""
    print(f"\n{'='*60}")
    print(f"Testing {bga_name} on {port_name}")
    print(f"{'='*60}")
    
    try:
        # Open serial connection
        print(f"🔌 Opening {port_name}...")
        ser = serial.Serial(
            port=port_name,
            baudrate=9600,
            bytesize=8,
            stopbits=1,
            parity='N',
            timeout=2
        )
        print(f"✅ {port_name} opened successfully")
        
        # Wait for device to be ready
        time.sleep(1)
        
        # Test 1: Device Identification
        print(f"\n📋 Step 1: Device Identification")
        idn_response = send_with_debug(ser, "*IDN?", "(Device ID)")
        
        if not idn_response:
            print(f"⚠️  No response to *IDN? - trying alternative commands...")
            # Try some alternative identification commands
            send_with_debug(ser, "VER?", "(Version)")
            send_with_debug(ser, "ID?", "(Alternative ID)")
            send_with_debug(ser, "MODEL?", "(Model)")
        
        # Test 2: Set Binary Gas Mode
        print(f"\n⚙️  Step 2: Setting Binary Gas Mode")
        send_with_debug(ser, "MSMD 1", "(Binary mode)")
        
        # Test 3: Configure Gases (based on our BGA 1 config)
        print(f"\n🧪 Step 3: Configuring Gases")
        send_with_debug(ser, "GASP 7782-44-7", "(Primary: O2)")
        send_with_debug(ser, "GASS 1333-74-0", "(Secondary: H2)")
        
        # Test 4: Read Measurements
        print(f"\n📊 Step 4: Reading Measurements")
        temp = send_with_debug(ser, "TCEL?", "(Temperature)")
        pressure = send_with_debug(ser, "PRES?", "(Pressure)")
        sos = send_with_debug(ser, "NSOS?", "(Speed of Sound)")
        ratio1 = send_with_debug(ser, "RATO? 1", "(Primary Gas %)")
        ratio2 = send_with_debug(ser, "RATO? 2", "(Secondary Gas %)")
        
        # Test 5: Summary
        print(f"\n📈 Step 5: Measurement Summary")
        print(f"  Temperature: {temp} °C")
        print(f"  Pressure: {pressure} psi")
        print(f"  Speed of Sound: {sos} m/s")
        print(f"  Primary Gas (O2): {ratio1} %")
        print(f"  Secondary Gas (H2): {ratio2} %")
        
        # Check if we got any valid measurements
        measurements = [temp, pressure, sos, ratio1, ratio2]
        valid_measurements = [m for m in measurements if m and m != '']
        
        if valid_measurements:
            print(f"✅ {bga_name} is responding - got {len(valid_measurements)}/5 measurements")
        else:
            print(f"❌ {bga_name} is not providing measurements")
            
            # Additional diagnostics
            print(f"\n🔧 Additional Diagnostics:")
            send_with_debug(ser, "STATUS?", "(Status check)")
            send_with_debug(ser, "ERR?", "(Error check)")
            send_with_debug(ser, "HELP", "(Help command)")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ Serial error on {port_name}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error on {port_name}: {e}")

def main():
    """Test all BGA ports"""
    print("🔬 BGA244 Comprehensive Debug Test")
    print(f"Platform: {platform.system()}")
    print(f"Testing all configured BGA ports...")
    
    # Test configuration based on our settings
    test_configs = [
        ("COM8", "BGA 1 (H2 Header)"),
        ("COM9", "BGA 2 (O2 Header)"), 
        # ("COM10", "BGA 3 (De-oxo)")  # Not connected yet
    ]
    
    for port, name in test_configs:
        test_bga_port(port, name)
    
    print(f"\n{'='*60}")
    print("🏁 Testing Complete")
    print("📝 Check the output above to identify which BGA has issues")
    print("💡 If BGA 1 shows 'No response' but port opens OK,")
    print("   the device might need different commands or settings")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 