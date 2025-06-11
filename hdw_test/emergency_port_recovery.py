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
    """Kill any other Python processes that might be holding COM ports (but not this one)"""
    print("🔪 Killing any Python processes that might be holding ports...")
    
    try:
        import psutil
        current_pid = os.getpid()
        print(f"   → Current script PID: {current_pid} (will NOT kill)")
        
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    if proc.info['pid'] != current_pid:
                        # Check if it's running main.py or related scripts
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'main.py' in cmdline or 'bga' in cmdline.lower():
                            print(f"   → Killing PID {proc.info['pid']}: {cmdline}")
                            proc.terminate()
                            killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if killed_count > 0:
            print(f"   → Killed {killed_count} Python processes")
            time.sleep(2.0)
        else:
            print(f"   → No other Python processes found")
        
        print("   ✅ Python process cleanup complete")
        
    except ImportError:
        print("   ⚠️  psutil not available, using basic taskkill...")
        # Fallback: Use a batch file to kill processes after this script exits
        create_cleanup_batch()
    except Exception as e:
        print(f"   ⚠️  Error with selective killing: {e}")
        create_cleanup_batch()


def create_cleanup_batch():
    """Create a batch file to kill Python processes after this script exits"""
    batch_content = '''@echo off
echo Waiting for emergency script to finish...
timeout /t 2 /nobreak >nul
echo Killing Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
echo Cleanup complete
del "%~f0"
'''
    
    with open('cleanup_python.bat', 'w') as f:
        f.write(batch_content)
    
    print("   → Created cleanup batch file to run after script exits")


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