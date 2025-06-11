#!/usr/bin/env python3
"""
Fix BGA 2 Communication Issues
Try different serial settings to fix corrupted communication with BGA 2
"""

import serial
import time

def test_serial_settings(port, baud, parity, stopbits, name):
    """Test specific serial settings"""
    print(f"\n🔧 Testing {name}:")
    print(f"   Port: {port}, Baud: {baud}, Parity: {parity}, Stop: {stopbits}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=8,
            stopbits=stopbits,
            parity=parity,
            timeout=2
        )
        time.sleep(1)
        
        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test device identification
        ser.write(b'*IDN?\r\n')
        time.sleep(0.3)
        response = ser.read_all().decode('ascii', errors='ignore').strip()
        
        ser.close()
        
        print(f"   Response: '{response}'")
        
        # Check if response is clean
        if "Stanford Research Systems,BGA244" in response:
            print(f"   ✅ PERFECT! Clean BGA244 response")
            return True, "perfect"
        elif "BGA244" in response:
            # Count corruption indicators
            corruption_chars = sum(1 for c in response if c in '?|<>[]{}')
            if corruption_chars == 0:
                print(f"   ✅ GOOD! Contains BGA244 and appears clean")
                return True, "good"
            else:
                print(f"   ⚠️  PARTIAL! Contains BGA244 but has {corruption_chars} corrupted characters")
                return False, "partial"
        else:
            print(f"   ❌ BAD! No BGA244 found in response")
            return False, "bad"
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False, "error"

def main():
    """Try different communication settings for BGA 2"""
    print("🔧 BGA 2 Communication Diagnostic")
    print("Trying different serial settings to fix corrupted communication...")
    
    port = "COM9"
    results = []
    
    # Test different combinations
    test_configs = [
        # (baud, parity, stopbits, name)
        (9600, 'N', 1, "Standard (9600, N, 1)"),
        (9600, 'E', 1, "Even Parity (9600, E, 1)"),
        (9600, 'O', 1, "Odd Parity (9600, O, 1)"),
        (9600, 'N', 2, "Two Stop Bits (9600, N, 2)"),
        (19200, 'N', 1, "Higher Baud (19200, N, 1)"),
        (4800, 'N', 1, "Lower Baud (4800, N, 1)"),
        (38400, 'N', 1, "High Baud (38400, N, 1)"),
        (19200, 'E', 1, "High Baud + Even Parity (19200, E, 1)"),
    ]
    
    print(f"\n🧪 Testing {len(test_configs)} different configurations on {port}:")
    
    best_result = None
    best_quality = "bad"
    
    for baud, parity, stopbits, name in test_configs:
        success, quality = test_serial_settings(port, baud, parity, stopbits, name)
        results.append((name, success, quality))
        
        # Track the best result
        quality_order = ["perfect", "good", "partial", "bad", "error"]
        if quality_order.index(quality) < quality_order.index(best_quality):
            best_result = (baud, parity, stopbits, name)
            best_quality = quality
    
    # Summary
    print(f"\n{'='*70}")
    print("🎯 COMMUNICATION TEST RESULTS:")
    print(f"{'='*70}")
    
    for name, success, quality in results:
        status = f"✅ {quality.upper()}" if success else f"❌ {quality.upper()}"
        print(f"   {name}: {status}")
    
    if best_result:
        baud, parity, stopbits, name = best_result
        print(f"\n🏆 BEST CONFIGURATION FOUND:")
        print(f"   {name}")
        print(f"   Settings: Baud={baud}, Parity='{parity}', StopBits={stopbits}")
        
        if best_quality == "perfect":
            print(f"   ✅ This configuration provides clean communication!")
            print(f"\n💡 SOLUTION:")
            print(f"   Update your BGA 2 configuration to use:")
            print(f"   - Baud Rate: {baud}")
            print(f"   - Parity: {parity}")  
            print(f"   - Stop Bits: {stopbits}")
        elif best_quality == "good":
            print(f"   ✅ This configuration works well!")
        else:
            print(f"   ⚠️  This is the best found, but communication is still poor")
            print(f"\n🔧 TROUBLESHOOTING SUGGESTIONS:")
            print(f"   • Check physical cable connections")
            print(f"   • Try a different USB cable")
            print(f"   • Check for electrical interference")
            print(f"   • Verify BGA 2 is not damaged")
    else:
        print(f"\n❌ NO WORKING CONFIGURATION FOUND")
        print(f"   This suggests a hardware problem with BGA 2")
    
    print(f"\n📝 Next Steps:")
    if best_quality in ["perfect", "good"]:
        print(f"   1. Update BGA 2 configuration with the best settings found")
        print(f"   2. Test both BGAs with the main application")
    else:
        print(f"   1. Check physical connections to BGA 2")
        print(f"   2. Try a different USB cable for BGA 2")
        print(f"   3. Test BGA 2 on a different computer/port")

if __name__ == "__main__":
    main() 