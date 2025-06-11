#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE BGA DIAGNOSIS
Figure out exactly what's broken and how to fix it
"""

import serial
import time
import subprocess
import os
import sys

def check_device_manager():
    """Check Windows Device Manager for COM port status"""
    print("🔍 CHECKING WINDOWS DEVICE MANAGER...")
    
    try:
        # Use wmic to query COM ports
        result = subprocess.run(['wmic', 'path', 'win32_pnpentity', 'where', 
                               'caption like "%COM%"', 'get', 'caption,status'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print("   📋 COM Ports in Device Manager:")
            for line in lines[1:]:  # Skip header
                if line.strip():
                    print(f"      {line.strip()}")
        else:
            print("   ❌ Could not query Device Manager")
            
    except Exception as e:
        print(f"   ❌ Error checking Device Manager: {e}")

def check_com_port_properties(port):
    """Check if we can even see the port in Windows"""
    print(f"\n🔍 CHECKING {port} PROPERTIES...")
    
    try:
        # Try to query the port using mode command
        result = subprocess.run(['mode', port], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {port} exists in Windows")
            print(f"      {result.stdout.strip()}")
        else:
            print(f"   ❌ {port} not found in Windows")
            print(f"      Error: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"   ❌ Error checking {port}: {e}")

def test_basic_serial_access(port):
    """Test if we can even open the serial port"""
    print(f"\n🔍 TESTING BASIC SERIAL ACCESS TO {port}...")
    
    try:
        # Try different serial settings
        settings = [
            {'baudrate': 9600, 'timeout': 1},
            {'baudrate': 115200, 'timeout': 1},
            {'baudrate': 9600, 'timeout': 0.1},
        ]
        
        for i, setting in enumerate(settings):
            print(f"   → Attempt {i+1}: {setting}")
            try:
                ser = serial.Serial(port, **setting)
                print(f"      ✅ Port opened successfully")
                
                # Check port status
                print(f"      → Is open: {ser.is_open}")
                print(f"      → In waiting: {ser.in_waiting}")
                print(f"      → Out waiting: {ser.out_waiting}")
                
                ser.close()
                print(f"      ✅ Port closed successfully")
                return True
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                
        return False
        
    except Exception as e:
        print(f"   ❌ Error testing {port}: {e}")
        return False

def test_hardware_communication(port):
    """Test actual hardware communication with multiple approaches"""
    print(f"\n🔍 TESTING HARDWARE COMMUNICATION ON {port}...")
    
    commands_to_try = [
        ('*IDN?', 'Device identification'),
        ('TCEL?', 'Temperature reading'),
        ('PRES?', 'Pressure reading'), 
        ('NSOS?', 'Speed of sound'),
        ('VERS?', 'Version info'),
        ('STAT?', 'Status'),
        ('', 'Empty command (CR/LF only)'),
    ]
    
    try:
        ser = serial.Serial(port, 9600, timeout=2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print(f"   📡 Trying {len(commands_to_try)} different commands...")
        
        responses_found = 0
        for cmd, desc in commands_to_try:
            print(f"   → {desc}: '{cmd}'")
            
            try:
                # Send command
                if cmd:
                    ser.write((cmd + '\r\n').encode('ascii'))
                else:
                    ser.write(b'\r\n')
                
                time.sleep(0.3)
                
                # Read response
                response = ser.read_all()
                if response:
                    decoded = response.decode('ascii', errors='ignore').strip()
                    print(f"      ✅ Response: '{decoded}'")
                    responses_found += 1
                else:
                    print(f"      ❌ No response")
                    
                # Clear buffers between commands
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                time.sleep(0.1)
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        ser.close()
        
        print(f"   📊 Found {responses_found}/{len(commands_to_try)} responses")
        return responses_found > 0
        
    except Exception as e:
        print(f"   ❌ Hardware test failed: {e}")
        return False

def main():
    """Run comprehensive diagnosis"""
    print("=" * 70)
    print("🏥 FINAL COMPREHENSIVE BGA DIAGNOSIS")
    print("=" * 70)
    print("Let's figure out exactly what's broken...\n")
    
    # Step 1: Check Windows Device Manager
    check_device_manager()
    
    # Step 2: Check each port properties
    for port in ['COM8', 'COM9']:
        check_com_port_properties(port)
    
    # Step 3: Test basic serial access
    print(f"\n" + "="*50)
    print("TESTING BASIC SERIAL PORT ACCESS")
    print("="*50)
    
    com8_serial_ok = test_basic_serial_access('COM8')
    com9_serial_ok = test_basic_serial_access('COM9')
    
    # Step 4: Test hardware communication
    print(f"\n" + "="*50)
    print("TESTING HARDWARE COMMUNICATION")
    print("="*50)
    
    com8_hw_ok = False
    com9_hw_ok = False
    
    if com8_serial_ok:
        com8_hw_ok = test_hardware_communication('COM8')
    
    if com9_serial_ok:
        com9_hw_ok = test_hardware_communication('COM9')
    
    # Final diagnosis
    print(f"\n" + "="*70)
    print("🩺 FINAL DIAGNOSIS")
    print("="*70)
    
    print(f"COM8 Serial Access: {'✅ OK' if com8_serial_ok else '❌ FAILED'}")
    print(f"COM8 Hardware:      {'✅ OK' if com8_hw_ok else '❌ FAILED'}")
    print(f"COM9 Serial Access: {'✅ OK' if com9_serial_ok else '❌ FAILED'}")
    print(f"COM9 Hardware:      {'✅ OK' if com9_hw_ok else '❌ FAILED'}")
    
    # Specific recommendations
    print(f"\n🎯 RECOMMENDED ACTIONS:")
    
    if not com9_serial_ok:
        print(f"❌ COM9 SERIAL PORT ISSUE:")
        print(f"   • COM9 port is not accessible in Windows")
        print(f"   • Check Device Manager for COM9 errors")
        print(f"   • Try unplugging/replugging the COM9 USB cable")
        print(f"   • The USB-to-serial driver may be corrupted")
        
    elif com9_serial_ok and not com9_hw_ok:
        print(f"❌ COM9 HARDWARE ISSUE:")
        print(f"   • Port opens fine but BGA device doesn't respond")
        print(f"   • BGA device may be powered off or in error state")
        print(f"   • Try power cycling the BGA device (unplug power)")
        print(f"   • Wrong device may be connected to COM9")
        
    elif com9_hw_ok:
        print(f"✅ COM9 IS WORKING!")
        print(f"   • Hardware responds to commands")
        print(f"   • The issue is in your main.py application")
        print(f"   • Try running main.py again - it should work now")
    
    print(f"\n🔧 NEXT STEPS:")
    
    if not com9_serial_ok:
        print(f"1. Open Windows Device Manager")
        print(f"2. Look for COM9 under 'Ports (COM & LPT)'")
        print(f"3. If COM9 has yellow warning, right-click → Update driver")
        print(f"4. If COM9 missing, unplug/replug USB cable")
        print(f"5. If still broken, restart computer")
        
    elif not com9_hw_ok:
        print(f"1. Unplug BGA power cable (not just USB)")
        print(f"2. Wait 30 seconds")
        print(f"3. Plug power back in")
        print(f"4. Wait for BGA to boot up (may take 1-2 minutes)")
        print(f"5. Run this diagnosis again")
        
    else:
        print(f"1. Try running your main.py again")
        print(f"2. If main.py still fails, the issue is in the application code")
        print(f"3. Try the simple_com9_test.py to confirm hardware works")


if __name__ == "__main__":
    main() 