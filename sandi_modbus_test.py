#!/usr/bin/env python3
"""
Minimal test script for Sandi SD1K120P power supply via RS-485 MODBUS-RTU
Uses Startech ICUSB422 USB to RS485 adapter
"""

from pymodbus.client import ModbusSerialClient
import time

# Configuration based on Sandi documentation
SLAVE_ADDRESS = 0xDD  # Default address from Sandi documentation
BAUD_RATE = 9600
DATA_BITS = 8
STOP_BITS = 1
PARITY = 'N'

# Register addresses from Sandi documentation (Table 4)
REGISTERS = {
    'charging_voltage': 0x0001,
    'charging_current': 0x0002,
    'charging_power': 0x0003,
    'charging_capacity': 0x0004,
    'charging_time': 0x0005,
    'battery_voltage': 0x0006,
    'system_fault': 0x0007,
    'module_fault': 0x0008,
    'module_temperature': 0x0009,
    'module_comm_status': 0x000A,
    'set_voltage_value': 0x000B,
    'set_current_value': 0x000C,
    'set_start_stop_status': 0x000D
}

def main():
    # Serial port - adjust based on your system
    # macOS: typically /dev/tty.usbserial-XXXX
    # Linux: typically /dev/ttyUSB0
    # Windows: typically COM3, COM4, etc.
    
    port = '/dev/tty.usbserial-A50285BI'  # ADJUST THIS FOR YOUR SYSTEM
    
    print(f"Attempting to connect to Sandi power supply on {port}")
    print(f"Settings: {BAUD_RATE} baud, {DATA_BITS}-{PARITY}-{STOP_BITS}")
    print("-" * 50)
    
    # Create MODBUS client
    client = ModbusSerialClient(
        port=port,
        baudrate=BAUD_RATE,
        bytesize=DATA_BITS,
        parity=PARITY,
        stopbits=STOP_BITS,
        timeout=1
    )
    
    # Connect to the device
    if not client.connect():
        print("ERROR: Failed to connect to MODBUS device")
        return
    
    print("Connected successfully")
    print("-" * 50)
    
    try:
        # Read all registers in one request (more efficient)
        # Reading from 0x0001 to 0x000D (13 registers)
        result = client.read_holding_registers(
            address=0x0001,
            count=13,
            slave=SLAVE_ADDRESS
        )
        
        if result.isError():
            print(f"ERROR reading registers: {result}")
            return
        
        # Parse and display results
        print("Power Supply Data:")
        print("-" * 50)
        
        # Process each register value
        register_values = result.registers
        
        # Voltage (0.1V resolution)
        print(f"Charging Voltage:     {register_values[0] * 0.1:.1f} V")
        print(f"Battery Voltage:      {register_values[5] * 0.1:.1f} V")
        print(f"Set Voltage Value:    {register_values[10] * 0.1:.1f} V")
        
        # Current (0.1A resolution)
        print(f"Charging Current:     {register_values[1] * 0.1:.1f} A")
        print(f"Set Current Value:    {register_values[11] * 0.1:.1f} A")
        
        # Power (0.1kW resolution)
        print(f"Charging Power:       {register_values[2] * 0.1:.1f} kW")
        
        # Capacity (0.1kWh resolution)
        print(f"Charging Capacity:    {register_values[3] * 0.1:.1f} kWh")
        
        # Time (minutes)
        print(f"Charging Time:        {register_values[4]} min")
        
        # Temperature (°C)
        print(f"Module Temperature:   {register_values[8]} °C")
        
        # Status fields
        print(f"System Fault:         0x{register_values[6]:04X}")
        print(f"Module Fault:         0x{register_values[7]:04X}")
        print(f"Module Comm Status:   {register_values[9]}")
        print(f"Start/Stop Status:    {'Started' if register_values[12] == 1 else 'Stopped'}")
        
    except Exception as e:
        print(f"ERROR: {e}")
    
    finally:
        client.close()
        print("-" * 50)
        print("Connection closed")

if __name__ == "__main__":
    # Note: Before running, ensure ICUSB422 DIP switches are set:
    # Switch 1: 485 (for 2-wire RS-485 mode)
    # Switch 2: No Echo
    # Switch 3: No Term (unless you need termination)
    
    main()