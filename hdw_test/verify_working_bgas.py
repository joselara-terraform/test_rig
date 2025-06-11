#!/usr/bin/env python3
"""
Verify Working BGAs
Simple verification of which BGAs are actually functioning
"""

import serial
import time

def test_bga_simple(port, name):
    """Simple test to see if a BGA is working"""
    print(f"\n{'='*50}")
    print(f"Testing {name} on {port}")
    print(f"{'='*50}")
    
    try:
        ser = serial.Serial(port, 9600, timeout=2)
        time.sleep(1)
        
        # Test 1: Device identification
        print("1. Device Identification:")
        ser.write(b'*IDN?\r\n')
        time.sleep(0.2)
        idn_response = ser.read_all().decode('ascii', errors='ignore').strip()
        print(f"   Response: '{idn_response}'")
        
        if "BGA244" in idn_response:
            print("   ✅ This IS a BGA244 device!")
            
            # Test 2: Get some measurements
            print("\n2. Testing Measurements:")
            
            # Temperature
            ser.write(b'TCEL?\r\n')
            time.sleep(0.2)
            temp = ser.read_all().decode('ascii', errors='ignore').strip()
            print(f"   Temperature: {temp} °C")
            
            # Gas ratios
            ser.write(b'RATO? 1\r\n')
            time.sleep(0.2)
            ratio1 = ser.read_all().decode('ascii', errors='ignore').strip()
            print(f"   Primary Gas: {ratio1} %")
            
            ser.write(b'RATO? 2\r\n')
            time.sleep(0.2)
            ratio2 = ser.read_all().decode('ascii', errors='ignore').strip()
            print(f"   Secondary Gas: {ratio2} %")
            
            if temp and ratio1 and ratio2:
                print(f"   ✅ {name} is WORKING and providing measurements!")
                return True
            else:
                print(f"   ❌ {name} identified as BGA244 but not providing measurements")
                return False
        else:
            print(f"   ❌ This is NOT a BGA244 device")
            print(f"   Raw response bytes: {repr(ser.read_all())}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        try:
            ser.close()
        except:
            pass

def main():
    print("🔬 BGA Working Verification Test")
    print("Checking which devices are actually working BGA244 units...")
    
    results = {}
    
    # Test both ports
    results["BGA 1 (COM8)"] = test_bga_simple("COM8", "BGA 1")
    results["BGA 2 (COM9)"] = test_bga_simple("COM9", "BGA 2")
    
    # Summary
    print(f"\n{'='*60}")
    print("🎯 SUMMARY - WORKING BGA244 DEVICES:")
    print(f"{'='*60}")
    
    working_bgas = []
    for name, working in results.items():
        status = "✅ WORKING" if working else "❌ NOT WORKING"
        print(f"   {name}: {status}")
        if working:
            working_bgas.append(name)
    
    print(f"\n📊 Total working BGA244 devices: {len(working_bgas)}")
    
    if working_bgas:
        print(f"✅ Working devices: {', '.join(working_bgas)}")
    else:
        print(f"❌ No working BGA244 devices found")
    
    print(f"\n💡 Next Steps:")
    if "BGA 1 (COM8)" in working_bgas:
        print(f"   • BGA 1 on COM8 is working - use it for testing")
    if "BGA 2 (COM9)" in working_bgas:
        print(f"   • BGA 2 on COM9 is working - use it for testing")
    if len(working_bgas) == 0:
        print(f"   • Check device connections and port assignments")
        print(f"   • Verify devices are actually BGA244 units")

if __name__ == "__main__":
    main() 