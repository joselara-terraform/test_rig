#!/usr/bin/env python3
"""
Minimal CVM24P Test Script
Reads channel 1 from each module every second and prints to terminal.
"""

import asyncio
import time
from xc2.bus import SerialBus
from xc2.consts import ProtocolEnum
from xc2.utils import get_serial_from_port
from xc2.xc2_dev_cvm24p import XC2Cvm24p

# Connection settings
CVM_PORT = "/dev/tty.usbserial-PW156329"  # Your specific device port
BAUD_RATE = 1000000  # 1MHz - standard for CVM24P

# Known module mapping (ordered by physical connection)
MODULES = {
    '158458': 0xA1,  # Module 1 - Channels 1-24
    '158436': 0xA6,  # Module 2 - Channels 25-48  
    '158435': 0xA7,  # Module 3 - Channels 49-72
    '158453': 0xA4,  # Module 4 - Channels 73-96
    '158340': 0xA9,  # Module 5 - Channels 97-120
}

# User-defined module names (maps serial to module name)
MODULE_NAMES = {
    '158458': 'Module 1',
    '158436': 'Module 2', 
    '158435': 'Module 3',
    '158453': 'Module 4',
    '158340': 'Module 5'
}

class CVM24PTest:
    def __init__(self):
        self.bus = None
        self.devices = {}  # serial -> XC2Cvm24p device
        
    async def connect(self):
        """Initialize connection and modules"""
        print("🔌 Connecting to CVM24P modules...")
        
        # Setup XC2 bus
        try:
            bus_sn = get_serial_from_port(CVM_PORT)
            self.bus = SerialBus(
                bus_sn,
                port=CVM_PORT,
                baud_rate=BAUD_RATE,
                protocol_type=ProtocolEnum.XC2
            )
            
            # Actually connect to the bus (CRITICAL STEP)
            await self.bus.connect()
            print(f"   ✅ XC2 bus connected to {CVM_PORT}")
            
            # Add stability pause for reliable communication
            await asyncio.sleep(2)
            print(f"   ✅ Bus stabilized")
            
        except Exception as e:
            print(f"   ❌ Failed to connect bus: {e}")
            return False
            
        # Initialize each module
        initialized_count = 0
        for serial, address in MODULES.items():
            try:
                module_name = MODULE_NAMES[serial]
                print(f"   🔧 Initializing {module_name} ({serial}) at 0x{address:X}...")
                device = XC2Cvm24p(self.bus, address)
                await device.initial_structure_reading()
                
                self.devices[serial] = device
                initialized_count += 1
                print(f"      ✅ {module_name} ready")
                
            except Exception as e:
                print(f"      ❌ Failed to initialize {MODULE_NAMES[serial]} ({serial}): {e}")
        
        if initialized_count == 0:
            print("❌ No modules initialized - exiting")
            return False
            
        print(f"🚀 {initialized_count}/{len(MODULES)} modules ready for testing")
        
        # Show module summary  
        print("   Ready modules:")
        for serial in self.devices.keys():
            module_name = MODULE_NAMES[serial]
            module_addr = MODULES[serial]
            print(f"      ✅ {module_name} - {serial} (0x{module_addr:X})")
        print()
        
        return True
        
    async def read_channel_1(self):
        """Read channel 1 voltage from each module"""
        readings = {}
        
        for serial, device in self.devices.items():
            try:
                # Read all voltages from module
                voltages = await device.read_and_get_reg_by_name("ch_V")
                # Get channel 1 (index 0)
                channel_1_voltage = voltages[0] if voltages and len(voltages) > 0 else 0.0
                readings[serial] = channel_1_voltage
                
            except Exception as e:
                # Uncomment for debugging: print(f"⚠️  Error reading module {serial}: {e}")
                readings[serial] = 0.0
                
        return readings
        

    async def test_loop(self):
        """Main test loop - read and print voltages"""
        print("📊 Starting voltage monitoring (Channel 1 only)...")
        print("   Press Ctrl+C to stop\n")
        
        while True:
            # Get timestamp
            timestamp = time.strftime("%H:%M:%S")
            
            # Read channel 1 from all modules
            readings = await self.read_channel_1()
            
            # Print results
            print(f"[{timestamp}] Channel 1 Voltages:")
            for serial, voltage in readings.items():
                module_addr = MODULES[serial]
                module_name = MODULE_NAMES[serial]
                print(f"   {module_name} - {serial} (0x{module_addr:X}): {voltage:.3f}V")
            print()  # Empty line for spacing
            
    def disconnect(self):
        """Clean shutdown"""
        print("🔌 Disconnecting...")
        # SerialBus automatically handles cleanup when object is destroyed
        self.bus = None
        self.devices.clear()
        print("   ✅ Disconnected")

async def main():
    """Main test function"""
    test = CVM24PTest()
    
    try:
        # Connect and initialize
        if await test.connect():
            # Run test loop
            await test.test_loop()
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Always cleanup
        test.disconnect()

if __name__ == "__main__":
    print("🧪 CVM24P Minimal Test Script")
    print("=" * 40)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Suppress the asyncio.run() KeyboardInterrupt traceback
        pass 