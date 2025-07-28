#!/usr/bin/env python3
"""
Minimal test script for Sandi SD1K120P power supply via RS-485 MODBUS-RTU
Uses Startech ICUSB422 USB to RS485 adapter: check correct port bu running: ls /dev/tty.*
"""

import serial
import time

# Configuration based on Sandi documentation
SLAVE_ADDRESS = 0x01  # Default address from Sandi documentation
BAUD_RATE = 9600
DATA_BITS = 8
STOP_BITS = 1
PARITY = None

port = '/dev/tty.usbserial-B0035Q79'

# Register addresses from Sandi documentation (Table 4)
REGISTERS = {

    # Read only
    'charging_voltage': {
        "address": 0x0001,
        "attribute": "RO",
        "description": "Charging voltage",
        "Symbol": "V",
        "Unit": 0.1,
    },
    'charging_current': {
        "address": 0x0002,
        "attribute": "RO",
        "description": "Charging current",
        "Symbol": "a",
        "Unit": 0.1,
    },
    'Ccharging_power': {
        "address": 0x0003,
        "attribute": "RO",
        "description": "Charging power",
        "Symbol": "kW",
        "Unit": 0.1,
    },
    'charging_capacity': {
        "address": 0x0004,
        "attribute": "RO",
        "description": "Charging capacity",
        "Symbol": "kWh",
        "Unit": 0.1,
    },
    'charging_time': {
        "address": 0x0005,
        "attribute": "RO",
        "description": "Charging time",
        "Symbol": "min",
        "Unit": 1,
    },
    'battery_voltage': {
        "address": 0x0006,
        "attribute": "RO",
        "description": "Battery voltage",
        "Symbol": "V",
        "Unit": 0.1,
    },
    'system_fault': {
        "address": 0x0007,
        "attribute": "RO",
        "description": "System fault",
        "Symbol": None,
        "Unit": None,
    },
    'module_fault': {
        "address": 0x0008,
        "attribute": "RO",
        "description": "Module fault",
        "Symbol": None,
        "Unit": None,
    },
    'module_temperature': {
        "address": 0x0009,
        "attribute": "RO",
        "description": "Module temperature",
        "Symbol": "C",
        "Unit": 1,
    },
    'module_com_status': {
        "address": 0x000A,
        "attribute": "RO",
        "description": "Module communication status",
        "Symbol": None,
        "Unit": None,
    },
    'set_voltage_value': {
        "address": 0x000B,
        "attribute": "RO",
        "description": "Set voltage value",
        "Symbol": "V",
        "Unit": 0.1,
    },
    'set_current_value': {
        "address": 0x000C,
        "attribute": "RO",
        "description": "Set current value",
        "Symbol": "A",
        "Unit": 0.1,
    },
    'set_start_stop_status': {
        "address": 0x000D,
        "attribute": "RO",
        "description": "Set start/stop status",
        "Symbol": None,
        "Unit": None,
    },

    # Write Only
    'set_voltage': {
        "address": 0x0101,
        "attribute": "WO",
        "description": "Set voltage",
        "Symbol": "V",
        "Unit": 0.1,
    },
    'set_current': {
        "address": 0x0102,
        "attribute": "WO",
        "description": "Set current",
        "Symbol": "A",
        "Unit": 0.1,
    },
    'set_start_stop': {
        "address": 0x0103,
        "attribute": "WO",
        "description": "Set start/stop",
        "Symbol": None,
        "Unit": None,
    }
}

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')  # Modbus uses LSB first

def crc_sum(data: bytes) -> bytes:
    # Simple 1-byte checksum: sum all bytes, keep lowest byte
    checksum = sum(data) & 0xFF
    return bytes([checksum])

# Switch between CRC functions
use_modbus_crc = False
crc_function = crc16 if use_modbus_crc else crc_sum

def read_all_ro_registers():
    with serial.Serial(port, baudrate=BAUD_RATE, bytesize=DATA_BITS, stopbits=STOP_BITS,
                       parity=PARITY if PARITY else 'N', timeout=2) as ser:

        start_addr = min(meta['address'] for meta in REGISTERS.values() if meta['attribute'] == 'RO')
        end_addr = max(meta['address'] for meta in REGISTERS.values() if meta['attribute'] == 'RO')
        num_regs = end_addr - start_addr + 1

        # Step 1: Create request without CRC
        request = bytearray()
        request.append(SLAVE_ADDRESS)
        request.append(0x03)
        request.extend(start_addr.to_bytes(2, 'big'))
        request.extend(num_regs.to_bytes(2, 'big'))

        # 🔧 Debug: Show raw frame before CRC
        print(f"[debug] Raw frame (no CRC): {request.hex()}")

        # Step 2: Compute CRC before appending
        crc = crc_function(request)

        # Step 3: Build full frame
        frame = request + crc

        # Step 4: Send it
        print(f"TX Frame: {frame.hex()}")
        ser.write(frame)

        print(f"Requesting {num_regs} registers starting at 0x{start_addr:04X}")

        ser.write(frame)
        expected_bytes = 5 + 2 * num_regs  # 1 addr + 1 func + 1 byte count + 2*num_regs + 2 CRC
        response = ser.read(expected_bytes)

        if len(response) < expected_bytes:
            print("[error] No or incomplete response")
            return

        if response[1] == 0x83:
            print(f"[error] Modbus exception code: {response[2]}")
            return

        print(f"RX Frame: {response.hex()}")

        byte_values = response[3:-2]  # Strip header and CRC
        for name, meta in REGISTERS.items():
            if meta['attribute'] != 'RO':
                continue
            offset = meta['address'] - start_addr
            raw = int.from_bytes(byte_values[2 * offset: 2 * offset + 2], byteorder='big')
            unit = meta.get("Unit") or 1
            scaled = raw * unit if isinstance(unit, (int, float)) else raw
            print(f"{name} ({meta['description']}): {scaled} {meta.get('Symbol') or ''}")

if __name__ == "__main__":
    read_all_ro_registers()
