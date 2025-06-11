#!/usr/bin/env python3
"""
COM3 Diagnostic Script
Test COM3 specifically to identify why it's not working
"""

import serial
import time

def test_port(port, description):
    """Test a specific COM port"""
    print(f"\n🔍 Testing {port} ({description})")
    print("=" * 50)
    
    try:
        # Try different timeout values
        for timeout in [1, 2, 5]:
            print(f"\n⏱️  Trying {port} with {timeout}s timeout...")
            
            try:
                ser = serial.Serial(port, 9600, timeout=timeout)
                print(f"   ✅ {port} opened successfully (timeout={timeout}s)")
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                print(f"   → Buffers cleared")
                
                # Wait a moment
                time.sleep(0.5)
                
                # Try sending *IDN?
                print(f"   → Sending *IDN? command...")
                ser.write(b'*IDN?\r\n')
                time.sleep(0.2)
                
                response = ser.read_all()
                print(f"   ← Raw response: {repr(response)}")
                
                decoded = response.decode('ascii', errors='ignore').strip()
                print(f"   ← Decoded: '{decoded}'")
                
                if decoded:
                    print(f"   ✅ Device responds on {port}!")
                    ser.close()
                    return True
                else:
                    print(f"   ❌ No response on {port}")
                
                ser.close()
                
            except serial.SerialException as e:
                print(f"   ❌ Serial error on {port}: {e}")
            except Exception as e:
                print(f"   ⚠️  Other error on {port}: {e}")
    
    except Exception as e:
        print(f"❌ Failed to test {port}: {e}")
    
    return False

def main():
    """Test COM3 vs COM4 to identify the difference"""
    print("🔧 COM3 vs COM4 Diagnostic Tool")
    print("=" * 60)
    
    # Test COM3 (problematic)
    com3_works = test_port('COM3', 'Problematic port')
    
    # Test COM4 (working)  
    com4_works = test_port('COM4', 'Working port')
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"=" * 30)
    print(f"COM3: {'✅ Working' if com3_works else '❌ Not working'}")
    print(f"COM4: {'✅ Working' if com4_works else '❌ Not working'}")
    
    if not com3_works:
        print(f"\n🔧 TROUBLESHOOTING COM3:")
        print(f"1. Check Windows Device Manager for COM3 status")
        print(f"2. Verify COM3 is not in use by another application")
        print(f"3. Try different COM3 settings (baud rate, flow control)")
        print(f"4. Check if COM3 exists vs. virtual/missing port")
        print(f"5. Try unplugging and reconnecting the USB device")

if __name__ == "__main__":
    main() 