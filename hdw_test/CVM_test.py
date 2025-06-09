import asyncio
import datetime
import time

from xc2.bus import SerialBus
from xc2.bus_utils import get_broadcast_echo, get_serial_broadcast
from xc2.consts import ProtocolEnum
from xc2.utils import discover_serial_ports, get_serial_from_port
from xc2.xc2_dev_cvm24p import XC2Cvm24p


async def discover_all_cvm_modules(bus, attempts=5, delay=1):
    """Find all modules through multiple discovery attempts"""
    found_modules = {}
    
    for attempt in range(attempts):
        # Pause between attempts
        await asyncio.sleep(delay)
        
        # Try to get devices via echo
        try:
            devices = await get_broadcast_echo(bus=bus)
            print(f"Scan {attempt+1}: Found {len(devices)} devices")
            
            # Try to get device info
            try:
                device_info = await get_serial_broadcast(bus=bus)
                
                # Add modules by serial number
                for addr, info in device_info.items():
                    serial = info['dev_serial']
                    if serial not in found_modules:
                        found_modules[serial] = {
                            'address': addr,
                            'type': info['dev_type'],
                            'serial': serial
                        }
            except Exception:
                pass
                
            # Add devices that responded to echo but not to serial query
            for addr in devices:
                found = False
                for module in found_modules.values():
                    if module['address'] == addr:
                        found = True
                        break
                
                if not found:
                    # Try to get serial directly
                    try:
                        device = XC2Cvm24p(bus, addr)
                        device_type, device_serial = await device.read_serial_number()
                        found_modules[device_serial] = {
                            'address': addr,
                            'type': device_type,
                            'serial': device_serial
                        }
                    except Exception:
                        # Add a placeholder if we can't get the serial
                        temp_serial = f"unknown_{addr:X}"
                        found_modules[temp_serial] = {
                            'address': addr,
                            'type': 'Unknown',
                            'serial': temp_serial
                        }
        except Exception:
            pass
    
    return found_modules


async def initialize_modules(modules, bus):
    """Initialize all modules and return the device objects"""
    initialized_modules = []
    print("\nInitializing modules...")
    
    for serial, info in modules.items():
        device = XC2Cvm24p(bus, info['address'])
        try:
            await device.initial_structure_reading()
            initialized_modules.append((device, serial, info['address']))
            print(f"Initialized module {serial} (Address: 0x{info['address']:X})")
        except Exception as e:
            print(f"Failed to initialize module {serial}: {e}")
    
    return initialized_modules


async def monitor_channel_1(modules, interval=1, duration=None):
    """
    Monitor channel 1 of all modules at the specified interval.
    
    Args:
        modules: List of tuples (device, serial, address)
        interval: Time between readings in seconds
        duration: How long to run the monitoring (None for indefinite)
    """
    print("\n=== Channel 1 Voltage Monitoring ===")
    print("Press Ctrl+C to stop monitoring")
    print("\nTimestamp                Module Serial    Address    Channel 1 Voltage")
    print("-------------------------------------------------------------------------")
    
    start_time = time.time()
    
    try:
        while True:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            readings = []
            
            # Read voltage from each module
            for device, serial, address in modules:
                try:
                    # Use read_and_get_reg_by_name for consistent readings
                    cell_voltages = await device.read_and_get_reg_by_name("ch_V")
                    channel_1_voltage = cell_voltages[0]  # Get channel 1 voltage
                    readings.append((serial, address, channel_1_voltage))
                except Exception as e:
                    readings.append((serial, address, f"Error: {str(e)[:20]}..."))
            
            # Print the readings
            for serial, address, voltage in readings:
                if isinstance(voltage, (int, float)):
                    print(f"{current_time}    {serial}      0x{address:X}       {voltage:.6f} V")
                else:
                    print(f"{current_time}    {serial}      0x{address:X}       {voltage}")
            
            # Check if we've reached the duration
            if duration and (time.time() - start_time) > duration:
                break
                
            # Print separator if multiple modules
            if len(modules) > 1:
                print("-------------------------------------------------------------------------")
                
            # Wait for the next interval
            await asyncio.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


async def main():
    # Find serial ports
    available_ports = discover_serial_ports()
    if not available_ports:
        print("No serial ports found. Make sure the device is connected.")
        return
    
    selected_port = available_ports[0]
    bus_sn = get_serial_from_port(selected_port)
    
    # Create and connect to bus - use 1000000 baud which we found works best
    baud_rate = 1000000
    print(f"Connecting to port {selected_port} with baud rate {baud_rate}...")
    my_bus = SerialBus(bus_sn, port=selected_port, baud_rate=baud_rate, protocol_type=ProtocolEnum.XC2)
    
    try:
        await my_bus.connect()
        print("Connected successfully.")
    except Exception as e:
        print(f"Error connecting: {e}")
        return
    
    # Pause for bus stability
    await asyncio.sleep(3)
    
    # Find all modules with multiple discovery attempts
    print("\nFinding all CVM24P modules...")
    modules = await discover_all_cvm_modules(my_bus)
    
    # Sort modules by address for consistent display
    modules_list = sorted(modules.items(), key=lambda x: x[1]['address'])
    
    print(f"\nFound {len(modules)} CVM24P modules:")
    for serial, info in modules_list:
        print(f"Module - Serial: {serial}, Address: 0x{info['address']:X}")
    
    # Initialize all modules
    initialized_modules = await initialize_modules(modules, my_bus)
    
    # Monitor channel 1 of each module indefinitely
    await monitor_channel_1(initialized_modules)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Program error: {e}")
    finally:
        print("\nMonitoring ended")