#!/usr/bin/env python3
"""
Sandi Electric DC Power Supply MODBUS-RTU Communication Test Script
Tests communication with the device without starting any power delivery
"""

import serial
import struct
import time
from typing import Optional, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SandiPowerSupply:
    """Class to communicate with Sandi Electric DC Power Supply via MODBUS-RTU"""
    
    def __init__(self, port: str, slave_address: int = 1):
        """
        Initialize the power supply communication
        
        Args:
            port: COM port (e.g., 'COM3' on Windows)
            slave_address: MODBUS slave address (default: 1)
        """
        self.port = port
        self.slave_address = slave_address
        self.ser = None
        
        # Register addresses from documentation
        self.REGISTERS = {
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
            'set_start_stop_status': 0x000D,
        }
        
        # Write registers
        self.WRITE_REGISTERS = {
            'set_voltage': 0x0101,
            'set_current': 0x0102,
            'set_start_stop': 0x0103,
        }
    
    def connect(self) -> bool:
        """
        Establish serial connection
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=1,
                timeout=1
            )
            logger.info(f"Connected to {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Disconnected")
    
    def calculate_crc16(self, data: bytes) -> int:
        """
        Calculate MODBUS CRC16
        
        Args:
            data: Bytes to calculate CRC for
            
        Returns:
            CRC16 value
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def build_read_request(self, register_address: int, num_registers: int = 1) -> bytes:
        """
        Build MODBUS RTU read request (function code 0x03)
        
        Args:
            register_address: Starting register address
            num_registers: Number of registers to read
            
        Returns:
            Complete MODBUS frame with CRC
        """
        # Build request without CRC
        request = struct.pack('>BBH H', 
                            self.slave_address,  # Slave address
                            0x03,               # Function code (read holding registers)
                            register_address,   # Register address
                            num_registers)      # Number of registers
        
        # Calculate and append CRC
        crc = self.calculate_crc16(request)
        request += struct.pack('<H', crc)  # CRC is little-endian
        
        return request
    
    def parse_response(self, response: bytes, num_registers: int) -> Optional[List[int]]:
        """
        Parse MODBUS response
        
        Args:
            response: Raw response bytes
            num_registers: Expected number of registers
            
        Returns:
            List of register values or None if error
        """
        if len(response) < 5:
            logger.error(f"Response too short: {response.hex()}")
            return None
        
        slave_addr = response[0]
        function_code = response[1]
        
        # Check for error response
        if function_code & 0x80:
            error_code = response[2]
            logger.error(f"MODBUS error response. Function: {hex(function_code)}, Error code: {hex(error_code)}")
            return None
        
        if function_code != 0x03:
            logger.error(f"Unexpected function code: {hex(function_code)}")
            return None
        
        byte_count = response[2]
        expected_bytes = num_registers * 2
        
        if byte_count != expected_bytes:
            logger.error(f"Unexpected byte count: {byte_count}, expected: {expected_bytes}")
            return None
        
        # Extract register values
        values = []
        for i in range(num_registers):
            offset = 3 + (i * 2)
            value = struct.unpack('>H', response[offset:offset+2])[0]
            values.append(value)
        
        # Verify CRC
        data_without_crc = response[:-2]
        received_crc = struct.unpack('<H', response[-2:])[0]
        calculated_crc = self.calculate_crc16(data_without_crc)
        
        if received_crc != calculated_crc:
            logger.error(f"CRC mismatch. Received: {hex(received_crc)}, Calculated: {hex(calculated_crc)}")
            return None
        
        return values
    
    def read_register(self, register_name: str) -> Optional[float]:
        """
        Read a single register by name
        
        Args:
            register_name: Name of register from REGISTERS dict
            
        Returns:
            Register value (scaled) or None if error
        """
        if register_name not in self.REGISTERS:
            logger.error(f"Unknown register: {register_name}")
            return None
        
        register_addr = self.REGISTERS[register_name]
        
        # Build and send request
        request = self.build_read_request(register_addr, 1)
        logger.debug(f"Sending request: {request.hex()}")
        
        try:
            self.ser.write(request)
            time.sleep(0.05)  # Small delay for response
            
            # Read response
            response = self.ser.read(7)  # Expected: addr + func + count + 2 bytes data + 2 bytes CRC
            if len(response) < 7:
                # Try to read more if available
                response += self.ser.read(self.ser.in_waiting)
            
            logger.debug(f"Received response: {response.hex()}")
            
            values = self.parse_response(response, 1)
            if values is None:
                return None
            
            # Apply scaling based on register type
            value = values[0]
            if register_name in ['charging_voltage', 'charging_current', 'charging_power', 
                               'charging_capacity', 'battery_voltage', 'set_voltage_value', 
                               'set_current_value']:
                return value / 10.0  # 0.1 scaling factor
            else:
                return float(value)
            
        except Exception as e:
            logger.error(f"Error reading register {register_name}: {e}")
            return None
    
    def read_all_status(self) -> dict:
        """
        Read all status registers
        
        Returns:
            Dictionary with all status values
        """
        status = {}
        
        # Read operational data
        for reg_name in ['charging_voltage', 'charging_current', 'charging_power', 
                        'charging_capacity', 'charging_time', 'battery_voltage']:
            value = self.read_register(reg_name)
            if value is not None:
                status[reg_name] = value
        
        # Read fault and status registers
        for reg_name in ['system_fault', 'module_fault', 'module_temperature', 
                        'module_comm_status', 'set_start_stop_status']:
            value = self.read_register(reg_name)
            if value is not None:
                status[reg_name] = value
        
        return status
    
    def decode_system_fault(self, fault_value: int) -> List[str]:
        """
        Decode system fault bits
        
        Args:
            fault_value: System fault register value
            
        Returns:
            List of active fault descriptions
        """
        faults = []
        fault_bits = {
            0: "Emergency stop fault",
            1: "LCD communication fault",
            2: "Rectifier Module Communication Fault",
            11: "Three-phase input phase loss alarm",
            12: "Three-phase input unbalance alarm",
            13: "Input under-voltage alarm",
            14: "Input over-voltage alarm",
        }
        
        for bit, description in fault_bits.items():
            if fault_value & (1 << bit):
                faults.append(description)
        
        # Module faults (bits 8-10)
        for i in range(8):
            if fault_value & (0x100 << i):
                faults.append(f"Rectifier module {i+1} fault")
        
        return faults


def main():
    """Main test function"""
    # Configuration
    # Windows: "COM3", "COM4", etc.
    # Mac: "/dev/tty.usbserial-XXXX" or "/dev/cu.usbserial-XXXX"
    # Linux: "/dev/ttyUSB0", "/dev/ttyUSB1", etc.
    COM_PORT = "/dev/tty.usbserial-B0035Q79"  # Your Mac's USB-RS485 adapter
    SLAVE_ADDRESS = 1  # Default slave address
    
    print("Sandi Electric DC Power Supply MODBUS-RTU Communication Test")
    print("=" * 60)
    
    # Create power supply instance
    ps = SandiPowerSupply(COM_PORT, SLAVE_ADDRESS)
    
    # Connect to device
    if not ps.connect():
        print("Failed to connect to device. Please check:")
        print("1. COM port is correct")
        print("2. RS485 adapter is connected")
        print("3. Power supply is powered on")
        return
    
    try:
        print(f"\nConnected to {COM_PORT}")
        print("\nTesting communication by reading status registers...")
        print("-" * 40)
        
        # Test individual register reads
        test_registers = [
            ('charging_voltage', 'V'),
            ('charging_current', 'A'),
            ('battery_voltage', 'V'),
            ('module_temperature', '°C'),
            ('set_start_stop_status', ''),
        ]
        
        success_count = 0
        for reg_name, unit in test_registers:
            value = ps.read_register(reg_name)
            if value is not None:
                print(f"{reg_name}: {value} {unit}")
                success_count += 1
            else:
                print(f"{reg_name}: Failed to read")
            time.sleep(0.1)  # Small delay between reads
        
        print(f"\nSuccessfully read {success_count}/{len(test_registers)} registers")
        
        # Read comprehensive status
        print("\n" + "-" * 40)
        print("Reading comprehensive status...")
        status = ps.read_all_status()
        
        if status:
            print("\nDevice Status:")
            print(f"  Charging Voltage: {status.get('charging_voltage', 'N/A')} V")
            print(f"  Charging Current: {status.get('charging_current', 'N/A')} A")
            print(f"  Charging Power: {status.get('charging_power', 'N/A')} kW")
            print(f"  Battery Voltage: {status.get('battery_voltage', 'N/A')} V")
            print(f"  Module Temperature: {status.get('module_temperature', 'N/A')} °C")
            print(f"  Start/Stop Status: {'Started' if status.get('set_start_stop_status') == 1 else 'Stopped'}")
            
            # Check for faults
            if 'system_fault' in status and status['system_fault'] > 0:
                faults = ps.decode_system_fault(int(status['system_fault']))
                print(f"\nActive System Faults:")
                for fault in faults:
                    print(f"  - {fault}")
            else:
                print("\nNo system faults detected")
        
        print("\n" + "=" * 60)
        print("Communication test completed successfully!")
        print("The device is responding to MODBUS commands.")
        print("\nIMPORTANT: This test only reads status. It does NOT start power delivery.")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        ps.disconnect()


if __name__ == "__main__":
    main()