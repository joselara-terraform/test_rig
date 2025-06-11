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
        
        # Send identification command
        ser.write(b'*IDN?\r\n')
        time.sleep(0.1)
        
        response = ser.read_all().decode('ascii', errors='ignore').strip()
        ser.close()
        
        if response:
            print(f"   ✅ {port} responds: '{response}'")
            return True
        else:
            print(f"   ❌ {port} does not respond to *IDN?")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing {port}: {e}")
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


if __name__ == "__main__":
    main() 