import asyncio

from xc2.bus import SerialBus
from xc2.bus_utils import get_broadcast_echo
from xc2.consts import ProtocolEnum
from xc2.utils import discover_serial_ports, get_serial_from_port
from xc2.xc2_dev_cvm24p import XC2Cvm24p  # Using CVM24P device class for S216P


async def main():
    # Communication settings
    baud_rate = 1000000  # 1 Mbps - typical default for Kolibrik devices
    device_address = 0xA1  # Default XC2 address for CVM devices, may need adjustment
    
    # Find the available serial ports
    available_ports = discover_serial_ports()
    if not available_ports:
        print("No serial ports found. Make sure the device is connected.")
        return
    
    print(f"Found serial ports: {available_ports}")
    selected_port = available_ports[0]  # Using the first found port
    
    # Get the serial number of the port
    bus_sn = get_serial_from_port(selected_port)
    
    # Create an XC2 bus instance
    print(f"Connecting to port {selected_port} with baud rate {baud_rate}...")
    my_bus = SerialBus(bus_sn, port=selected_port, baud_rate=baud_rate, protocol_type=ProtocolEnum.XC2)
    
    # Connect to the bus
    try:
        await my_bus.connect()
        print("Successfully connected to the bus.")
    except Exception as e:
        print(f"Error connecting to the bus: {e}")
        return
    
    # Scan for devices on the bus
    try:
        devices = await get_broadcast_echo(bus=my_bus)
        print(f"Found devices: {devices}")
        
        if not devices:
            print("No devices found on the bus.")
            return
        
        if device_address not in devices:
            print(f"Device with address 0x{device_address:X} not found.")
            print(f"Available devices: {', '.join([f'0x{addr:X}' for addr in devices])}")
            return
    except Exception as e:
        print(f"Error scanning for devices: {e}")
        return
    
    # Create a device instance
    print(f"Creating device instance for address 0x{device_address:X}...")
    device = XC2Cvm24p(my_bus, device_address)
    
    # Read the registry structure
    try:
        print("Reading device structure...")
        await device.initial_structure_reading()
        print("Device structure read successfully.")
    except Exception as e:
        print(f"Error reading device structure: {e}")
        return
    
    # Get voltage data
    try:
        print("Reading cell voltages...")
        await device.get_app_status()
        
        # Display general information
        print(f"Timestamp: {device.timestamp}")
        print(f"Voltage sum: {device.ch_sum} V")
        
        # Display individual cell voltages
        print("\nCell Voltages:")
        for i, voltage in enumerate(device.v_channels):
            print(f"Cell {i+1}: {voltage:.4f} V")
        
        # Read averaged cell voltages
        print("\nReading averaged cell voltages...")
        await device.read_reg_by_name("ch_avg_V")
        avg_voltages = await device.get_reg_by_name("ch_avg_V")
        
        print("Averaged Cell Voltages:")
        for i, voltage in enumerate(avg_voltages):
            print(f"Cell {i+1} (avg): {voltage:.4f} V")
        
        # Read current cell voltages directly
        print("\nReading current cell voltages...")
        current_voltages = await device.read_and_get_reg_by_name("ch_V")
        
        print("Current Cell Voltages:")
        for i, voltage in enumerate(current_voltages):
            print(f"Cell {i+1} (current): {voltage:.4f} V")
            
    except Exception as e:
        print(f"Error reading cell voltages: {e}")
        return
    
    # Additional device information
    try:
        # Get device serial number
        device_type, device_serial = await device.read_serial_number()
        print(f"\nDevice Type: {device_type}")
        print(f"Device Serial Number: {device_serial}")
        
        # Get device features
        features = await device.read_feature()
        print("\nDevice Features:")
        print(f"Product ID: {features[0]}")
        print(f"Vendor ID: {features[1]}")
        print(f"Version: {features[2]}")
        print(f"Custom 1: {features[3]}")
        print(f"Custom 2: {features[4]}")
    except Exception as e:
        print(f"Error reading device information: {e}")


if __name__ == "__main__":
    asyncio.run(main())