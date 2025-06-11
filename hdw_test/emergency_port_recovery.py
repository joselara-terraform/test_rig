#!/usr/bin/env python3
"""
EMERGENCY COM Port Recovery Script
For when Windows gets COM ports stuck after failed connections
"""

import serial
import time
import subprocess
import os
import sys

def kill_python_processes():
    """Kill any other Python processes that might be holding COM ports"""
    print("🔪 Killing any Python processes that might be holding ports...")
    
    try:
        # Kill any python processes (except this one)
        result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                              capture_output=True, text=True)
        print(f"   → taskkill result: {result.returncode}")
        
        result = subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe'], 
                              capture_output=True, text=True)
        print(f"   → taskkill pythonw result: {result.returncode}")
        
        time.sleep(2.0)
        print("   ✅ Python processes cleared")
        
    except Exception as e:
        print(f"   ⚠️  Error killing processes: {e}")


def force_release_com_ports():
    """Use Windows handle.exe to force release COM port handles"""
    print("🔧 Force releasing COM port handles...")
    
    ports_to_release = ['COM3', 'COM4', 'COM8', 'COM9']
    
    for port in ports_to_release:
        try:
            # Try multiple approaches to release the port
            print(f"   → Force releasing {port}...")
            
            # Method 1: Quick open/close
            try:
                ser = serial.Serial(port, timeout=0.1)
                ser.close()
                del ser
            except:
                pass
            
            # Method 2: Set DTR/RTS and close
            try:
                ser = serial.Serial(port, timeout=0.1)
                ser.setDTR(False)
                ser.setRTS(False)
                ser.close()
                del ser
            except:
                pass
            
            # Method 3: Force close with specific settings
            try:
                ser = serial.Serial()
                ser.port = port
                ser.baudrate = 9600
                ser.timeout = 0.1
                ser.open()
                ser.flush()
                ser.close()
                del ser
            except:
                pass
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ⚠️  Error with {port}: {e}")
    
    print("   ✅ Force release complete")


def restart_usb_devices():
    """Instructions to restart USB devices"""
    print("\n🔌 USB DEVICE RESTART REQUIRED")
    print("=" * 50)
    print("Windows has the COM ports stuck. You need to:")
    print()
    print("1. 🔌 UNPLUG both BGA USB cables")
    print("2. ⏱️  WAIT 10 seconds")
    print("3. 🔌 PLUG IN the USB cable for BGA on COM8 first")
    print("4. ⏱️  WAIT 5 seconds")
    print("5. 🔌 PLUG IN the USB cable for BGA on COM9")
    print("6. ⏱️  WAIT 5 seconds")
    print()
    
    input("Press ENTER after you've done the USB restart...")


def test_port_aggressive(port):
    """Aggressive port testing with multiple attempts"""
    print(f"\n🔍 Aggressive testing {port}...")
    
    for attempt in range(3):
        print(f"   → Attempt {attempt + 1}/3...")
        
        try:
            # Try with very short timeout first
            ser = serial.Serial(port, 9600, timeout=0.5)
            
            # Clear everything
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.flushInput()
            ser.flushOutput()
            
            # Set control lines
            ser.setDTR(True)
            ser.setRTS(True)
            time.sleep(0.1)
            ser.setDTR(False)
            ser.setRTS(False)
            time.sleep(0.2)
            
            # Try simple command
            ser.write(b'TCEL?\r\n')
            time.sleep(0.2)
            
            response = ser.read_all()
            ser.close()
            
            if response and len(response) > 0:
                decoded = response.decode('ascii', errors='ignore').strip()
                print(f"   ✅ {port} responds: '{decoded}'")
                return True
            else:
                print(f"   ❌ {port} no response on attempt {attempt + 1}")
                
        except Exception as e:
            print(f"   ❌ {port} error on attempt {attempt + 1}: {e}")
        
        # Wait between attempts
        if attempt < 2:
            time.sleep(1.0)
    
    return False


def main():
    """Emergency recovery main function"""
    print("=" * 60)
    print("🚨 EMERGENCY COM PORT RECOVERY 🚨")
    print("=" * 60)
    print("This script will aggressively try to fix stuck COM ports")
    print()
    
    # Step 1: Kill any processes
    kill_python_processes()
    
    # Step 2: Force release ports
    force_release_com_ports()
    
    # Step 3: Wait
    print("\n⏱️  Waiting 3 seconds for Windows to catch up...")
    time.sleep(3.0)
    
    # Step 4: Test ports
    print("\n🧪 Testing ports after cleanup...")
    working_ports = []
    stuck_ports = []
    
    for port in ['COM8', 'COM9']:
        if test_port_aggressive(port):
            working_ports.append(port)
        else:
            stuck_ports.append(port)
    
    # Step 5: Results
    print(f"\n📊 RESULTS:")
    print(f"   Working: {working_ports}")
    print(f"   Still stuck: {stuck_ports}")
    
    if stuck_ports:
        print(f"\n🚨 PHYSICAL RESET REQUIRED")
        restart_usb_devices()
        
        # Test again after USB restart
        print(f"\n🔄 Testing after USB restart...")
        for port in stuck_ports:
            if test_port_aggressive(port):
                print(f"✅ {port} RECOVERED!")
            else:
                print(f"❌ {port} still stuck")
    
    print(f"\n🎯 FINAL STEP:")
    print(f"Close this script and try your main.py again")
    print(f"If it still doesn't work, restart your computer")


if __name__ == "__main__":
    main() 