#!/usr/bin/env python3
"""
Diagnose COM9 Issue
Figure out why BGA 2 on COM9 suddenly stopped responding
"""

import serial
import time
import serial.tools.list_ports

def check_port_availability():
    """Check which COM ports are available"""
    print("🔍 Checking available COM ports...")
    ports = serial.tools.list_ports.comports()
    
    available_ports = []
    for port in ports:
        print(f"   📍 {port.device}: {port.description}")
        if port.hwid:
            print(f"      Hardware ID: {port.hwid}")
        available_ports.append(port.device)
    
    return available_ports

def test_port_basic_access(port):
    """Test if we can even open the port"""
    print(f"\n🔌 Testing basic access to {port}...")
    
    try:
        # Try to open the port
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = 9600
        ser.timeout = 1
        
        print(f"   → Attempting to open {port}...")
        ser.open()
        print(f"   ✅ Port {port} opened successfully")
        
        # Check port properties
        print(f"   → Port properties:")
        print(f"     • Is open: {ser.is_open}")
        print(f"     • Baudrate: {ser.baudrate}")
        print(f"     • Timeout: {ser.timeout}")
        print(f"     • Bytes waiting: {ser.in_waiting}")
        
        # Check if there's any existing data
        if ser.in_waiting > 0:
            existing_data = ser.read_all()
            print(f"     • Existing data in buffer: {repr(existing_data)}")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"   ❌ Cannot open {port}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error with {port}: {e}")
        return False

def test_port_communication(port):
    """Test if device responds to commands"""
    print(f"\n📡 Testing communication with {port}...")
    
    try:
        ser = serial.Serial(port, 9600, timeout=3)
        time.sleep(1)  # Give device time to wake up
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"   → Buffers cleared")
        
        # Try different approaches to wake up the device
        commands_to_try = [
            (b'*IDN?\r\n', "Standard identification"),
            (b'*IDN?\n', "Just LF termination"),
            (b'*IDN?\r', "Just CR termination"),
            (b'\r\n*IDN?\r\n', "With wake-up CRLF"),
            (b'\r\n\r\n*IDN?\r\n', "Multiple wake-up"),
            (b'HELLO\r\n', "Simple hello"),
            (b'\x03\r\n', "Ctrl+C wake up"),
        ]
        
        for cmd_bytes, description in commands_to_try:
            print(f"\n   🧪 Trying: {description}")
            print(f"      Sending: {repr(cmd_bytes)}")
            
            # Clear any existing data
            if ser.in_waiting > 0:
                old_data = ser.read_all()
                print(f"      Cleared: {repr(old_data)}")
            
            # Send command
            bytes_written = ser.write(cmd_bytes)
            ser.flush()
            print(f"      Bytes written: {bytes_written}")
            
            # Wait for response with progressively longer timeouts
            for wait_time in [0.2, 0.5, 1.0, 2.0]:
                time.sleep(wait_time)
                if ser.in_waiting > 0:
                    response = ser.read_all()
                    response_text = response.decode('ascii', errors='ignore').strip()
                    print(f"      ✅ Response after {wait_time}s: {repr(response)}")
                    print(f"      ✅ Decoded: '{response_text}'")
                    
                    if "BGA244" in response_text or len(response_text) > 0:
                        ser.close()
                        return True, response_text
                    break
            else:
                print(f"      ❌ No response to {description}")
        
        ser.close()
        return False, None
        
    except Exception as e:
        print(f"   ❌ Communication error: {e}")
        return False, None

def check_for_conflicts():
    """Check if another process might be using COM9"""
    print(f"\n🔒 Checking for potential port conflicts...")
    
    # Try to open COM9 multiple times quickly
    for i in range(3):
        try:
            ser = serial.Serial("COM9", 9600, timeout=0.1)
            print(f"   ✅ Attempt {i+1}: COM9 opened successfully")
            ser.close()
            time.sleep(0.1)
        except serial.SerialException as e:
            print(f"   ❌ Attempt {i+1}: {e}")
            if "already open" in str(e).lower() or "access denied" in str(e).lower():
                print(f"   ⚠️  COM9 might be in use by another application!")
                return True
    
    return False

def main():
    """Diagnose COM9 issue"""
    print("🔬 COM9 Diagnostic - Why did BGA 2 stop responding?")
    print("=" * 60)
    
    # Step 1: Check available ports
    available_ports = check_port_availability()
    
    if "COM9" not in available_ports:
        print(f"\n❌ COM9 is not in the list of available ports!")
        print(f"   Possible causes:")
        print(f"   • USB cable disconnected")
        print(f"   • Device powered off")
        print(f"   • Driver issue")
        print(f"   • Port reassigned to different number")
        return
    else:
        print(f"\n✅ COM9 is listed as available")
    
    # Step 2: Check for conflicts
    has_conflict = check_for_conflicts()
    if has_conflict:
        print(f"\n⚠️  Potential conflict detected!")
        print(f"   Try closing other applications that might use COM9")
        print(f"   Common culprits: Terminal programs, Arduino IDE, other test scripts")
    
    # Step 3: Test basic access
    can_open = test_port_basic_access("COM9")
    if not can_open:
        print(f"\n❌ Cannot even open COM9 - this is a driver/hardware issue")
        return
    
    # Step 4: Test communication
    can_communicate, response = test_port_communication("COM9")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"🎯 DIAGNOSTIC SUMMARY:")
    print(f"{'='*60}")
    print(f"   COM9 Available: {'✅' if 'COM9' in available_ports else '❌'}")
    print(f"   Can Open Port: {'✅' if can_open else '❌'}")
    print(f"   Device Responds: {'✅' if can_communicate else '❌'}")
    print(f"   Port Conflicts: {'⚠️' if has_conflict else '✅'}")
    
    if can_communicate:
        print(f"\n🎉 GOOD NEWS: Device is responding!")
        print(f"   Response: '{response}'")
        print(f"   Try running your verification script again.")
    else:
        print(f"\n🔧 TROUBLESHOOTING STEPS:")
        print(f"   1. Unplug and reconnect the USB cable for BGA 2")
        print(f"   2. Wait 10 seconds, then try again")
        print(f"   3. Check if BGA 2 has a power switch/button")
        print(f"   4. Try a different USB port")
        print(f"   5. Restart Windows Device Manager and rescan")

if __name__ == "__main__":
    main() 