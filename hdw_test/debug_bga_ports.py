#!/usr/bin/env python3
"""
BGA COM Port Debug and Recovery Script
Use this when BGA ports get stuck after failed connections
"""

import serial
import time
import sys
import os

# Add parent directory to path so we can import from services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bga244 import BGA244Service


def force_close_port(port):
    """Force close a specific COM port"""
    print(f"🔧 Force closing {port}...")
    
    try:
        # Try to open and immediately close to force release
        ser = serial.Serial(port, timeout=0.1)
        ser.close()
        time.sleep(0.2)
        print(f"   ✅ {port} successfully closed")
        return True
    except Exception as e:
        print(f"   ❌ Could not access {port}: {e}")
        return False


def test_port_communication(port):
    """Test if a port responds to BGA244 commands"""
    print(f"📡 Testing communication on {port}...")
    
    try:
        ser = serial.Serial(port, 9600, timeout=2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.2)
        
        # First try identification command
        print(f"   → Trying *IDN? command...")
        ser.write(b'*IDN?\r\n')
        time.sleep(0.1)
        
        response = ser.read_all().decode('ascii', errors='ignore').strip()
        if response:
            print(f"   ✅ {port} responds to *IDN?: '{response}'")
            ser.close()
            return True
        
        # If *IDN? doesn't work, try actual BGA244 commands
        print(f"   → *IDN? failed, trying BGA244 commands...")
        
        # Clear buffers again
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        # Try temperature reading (like BGA_test.py)
        ser.write(b'TCEL?\r\n')
        time.sleep(0.1)
        
        temp_response = ser.read_all().decode('ascii', errors='ignore').strip()
        if temp_response and temp_response != '':
            print(f"   ✅ {port} responds to TCEL?: '{temp_response}'")
            ser.close()
            return True
        
        # Try pressure reading
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        ser.write(b'PRES?\r\n')
        time.sleep(0.1)
        
        pres_response = ser.read_all().decode('ascii', errors='ignore').strip()
        if pres_response and pres_response != '':
            print(f"   ✅ {port} responds to PRES?: '{pres_response}'")
            ser.close()
            return True
        
        ser.close()
        print(f"   ❌ {port} does not respond to any BGA244 commands")
        return False
            
    except Exception as e:
        print(f"   ❌ Error testing {port}: {e}")
        return False


def run_bga_test(port):
    """Run a quick BGA test like the original BGA_test.py"""
    print(f"🧪 Running full BGA test on {port}...")
    
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        def send(cmd):
            ser.write((cmd + '\r\n').encode('ascii'))
            time.sleep(0.1)
            return ser.read_all().decode('ascii', errors='ignore').strip()
        
        # Set mode and gases (like BGA_test.py)
        print(f"   → Setting binary gas mode...")
        mode_resp = send("MSMD 1")
        print(f"   → MSMD 1: '{mode_resp}'")
        
        print(f"   → Configuring gases...")
        gas1_resp = send("GASP 7782-44-7")  # Primary gas: O2
        gas2_resp = send("GASS 7727-37-9")  # Secondary gas: N2
        print(f"   → GASP: '{gas1_resp}'")
        print(f"   → GASS: '{gas2_resp}'")
        
        # Read values
        print(f"   → Reading measurements...")
        temp = send("TCEL?")
        pressure = send("PRES?")
        sos = send("NSOS?")
        primary_gas = send("RATO? 1")
        
        print(f"   📊 Results:")
        print(f"      Temperature: {temp}°C")
        print(f"      Pressure: {pressure} psi")
        print(f"      Speed of Sound: {sos} m/s")
        print(f"      Primary Gas: {primary_gas}%")
        
        ser.close()
        
        # Check if we got meaningful responses
        if temp and pressure and sos:
            print(f"   ✅ {port} BGA test SUCCESSFUL!")
            return True
        else:
            print(f"   ❌ {port} BGA test FAILED - no valid readings")
            return False
            
    except Exception as e:
        print(f"   ❌ Error running BGA test on {port}: {e}")
        return False


def main():
    """Main debug and recovery function"""
    print("=" * 60)
    print("BGA COM Port Debug and Recovery Tool")
    print("=" * 60)
    
    # Ports to check
    ports_to_check = ['COM3', 'COM4', 'COM8', 'COM9']
    
    print("\n🔍 Step 1: Testing current port status...")
    working_ports = []
    stuck_ports = []
    
    for port in ports_to_check:
        if test_port_communication(port):
            working_ports.append(port)
        else:
            stuck_ports.append(port)
    
    print(f"\n📊 Results:")
    print(f"   Working ports: {working_ports if working_ports else 'None'}")
    print(f"   Non-responsive ports: {stuck_ports if stuck_ports else 'None'}")
    
    if stuck_ports:
        print(f"\n🔧 Step 2: Attempting to recover stuck ports...")
        
        # Try to force close stuck ports
        for port in stuck_ports:
            force_close_port(port)
        
        # Wait a moment
        time.sleep(1.0)
        
        # Test again
        print(f"\n🔄 Step 3: Re-testing after recovery...")
        recovered_ports = []
        still_stuck = []
        
        for port in stuck_ports:
            if test_port_communication(port):
                recovered_ports.append(port)
            else:
                still_stuck.append(port)
        
        print(f"\n📊 Recovery Results:")
        print(f"   Recovered ports: {recovered_ports if recovered_ports else 'None'}")
        print(f"   Still stuck: {still_stuck if still_stuck else 'None'}")
        
        if still_stuck:
            print(f"\n⚠️  Manual intervention needed for: {still_stuck}")
            print(f"   Try:")
            print(f"   1. Close any other applications using these ports")
            print(f"   2. Unplug and reconnect the USB cables")
            print(f"   3. Restart the application")
    
    print(f"\n🧪 Step 4: Testing BGA service cleanup...")
    try:
        bga_service = BGA244Service()
        bga_service.force_cleanup_all_ports()
        print(f"   ✅ BGA service cleanup completed")
    except Exception as e:
        print(f"   ❌ BGA service cleanup failed: {e}")
    
    print(f"\n✅ Debug and recovery complete!")
    print(f"   You should now be able to run your tests again.")


def run_interactive_tests():
    """Run interactive BGA tests on specific ports"""
    print("\n" + "=" * 60)
    print("Interactive BGA Testing")
    print("=" * 60)
    
    while True:
        print(f"\nChoose an option:")
        print(f"1. Test COM8 (like original BGA_test.py)")
        print(f"2. Test COM9 (like original BGA_test.py)")
        print(f"3. Test COM3")
        print(f"4. Test COM4")
        print(f"5. Test all ports")
        print(f"6. Exit")
        
        choice = input(f"\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            run_bga_test('COM8')
        elif choice == '2':
            run_bga_test('COM9')
        elif choice == '3':
            run_bga_test('COM3')
        elif choice == '4':
            run_bga_test('COM4')
        elif choice == '5':
            for port in ['COM3', 'COM4', 'COM8', 'COM9']:
                run_bga_test(port)
                print()
        elif choice == '6':
            break
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()
    
    # Ask if user wants to run interactive tests
    print(f"\n" + "=" * 60)
    response = input(f"Would you like to run interactive BGA tests? (y/n): ").strip().lower()
    if response in ['y', 'yes']:
        run_interactive_tests()
    
    print(f"\n🎯 All done! Your BGAs should be ready for use.") 