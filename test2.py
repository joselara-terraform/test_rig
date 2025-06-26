import serial
import time

def calculate_crc(data):
    """Calculate Modbus CRC16"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if (crc & 0x0001):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

def scan_single_register(port, address):
    """Try to read a single register"""
    request = bytearray([
        0x01,  # Slave ID
        0x03,  # Function code (read holding registers)
        (address >> 8) & 0xFF,  # Address high byte
        address & 0xFF,         # Address low byte
        0x00,  # Number of registers high
        0x01   # Number of registers low
    ])
    request += calculate_crc(request)
    
    port.reset_input_buffer()
    port.write(request)
    time.sleep(0.05)
    
    response = port.read(256)
    
    if response and len(response) >= 5:
        if response[1] == 0x03:  # Valid read response
            byte_count = response[2]
            if byte_count == 0x02 and len(response) >= 7:
                value = (response[3] << 8) | response[4]
                return ('success', value)
            elif byte_count == 0x09:  # Custom format
                if len(response) >= 6:
                    word1 = (response[3] << 8) | response[4]
                    return ('custom', word1)
        elif response[1] == 0x83:  # Error response
            error_code = response[2] if len(response) > 2 else 0
            return ('error', error_code)
    
    return (None, None)

def scan_register_range(port, start_addr, end_addr):
    """Scan a range of registers"""
    print(f"\nScanning registers 0x{start_addr:04X} to 0x{end_addr:04X}...")
    print("Address | Status  | Value   | Scaled 0.1 | Scaled 0.001 | Notes")
    print("-" * 70)
    
    found_registers = {}
    
    for addr in range(start_addr, end_addr + 1):
        status, value = scan_single_register(port, addr)
        
        if status == 'success':
            scaled_01 = value * 0.1
            scaled_001 = value * 0.001
            notes = ""
            
            # Check if this could be current (0-390A range)
            if 0 <= scaled_01 <= 390:
                notes += "Could be current? "
            
            # Check if this could be power (0-120kW range)
            if 0 <= scaled_01 <= 120:
                notes += "Could be power? "
                
            # Check if value matches our known voltage
            if 0.8 <= scaled_001 <= 1.2:
                notes += "Matches voltage pattern! "
            
            print(f"0x{addr:04X} | SUCCESS | {value:5d} | {scaled_01:8.1f} | {scaled_001:10.3f} | {notes}")
            found_registers[addr] = value
            
        elif status == 'custom':
            scaled_001 = value * 0.001
            print(f"0x{addr:04X} | CUSTOM  | {value:5d} |          | {scaled_001:10.3f} | Custom format")
            found_registers[addr] = value
            
        elif status == 'error':
            if value == 2:  # Illegal address
                pass  # Don't print, too noisy
            else:
                print(f"0x{addr:04X} | ERROR   | Code: {value}")
        
        time.sleep(0.02)  # Don't overwhelm the device
    
    return found_registers

def test_multi_register_read(port, start_addr, count):
    """Test reading multiple registers at once"""
    request = bytearray([
        0x01,  # Slave ID
        0x03,  # Function code
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    ])
    request += calculate_crc(request)
    
    port.reset_input_buffer()
    port.write(request)
    time.sleep(0.1)
    
    response = port.read(256)
    
    if response and len(response) >= 5:
        if response[1] == 0x03:
            byte_count = response[2]
            if byte_count == count * 2 and len(response) >= 3 + byte_count + 2:
                values = []
                for i in range(count):
                    idx = 3 + i * 2
                    if idx + 1 < len(response):
                        value = (response[idx] << 8) | response[idx + 1]
                        values.append(value)
                return values
    
    return None

def main():
    port = serial.Serial(
        port='/dev/cu.usbserial-B0035Q79',
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=0.5
    )
    
    print("Modbus Register Scanner for Sandi Charger")
    print("=" * 70)
    
    while True:
        print("\n1. Scan standard registers (0x0001-0x0010)")
        print("2. Scan extended registers (0x0100-0x0110)")
        print("3. Scan high registers (0x1000-0x1010)")
        print("4. Test specific multi-register read")
        print("5. Scan custom range")
        print("q. Quit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            found = scan_register_range(port, 0x0001, 0x0010)
            
            print(f"\nFound {len(found)} accessible registers")
            
            # Try reading as a block
            print("\nTrying to read 0x0001-0x0004 as a block:")
            values = test_multi_register_read(port, 0x0001, 4)
            if values:
                print(f"  Values: {values}")
                print(f"  As 0.1 scale: {[v*0.1 for v in values]}")
                print(f"  As 0.001 scale: {[v*0.001 for v in values]}")
                
        elif choice == '2':
            scan_register_range(port, 0x0100, 0x0110)
            
        elif choice == '3':
            scan_register_range(port, 0x1000, 0x1010)
            
        elif choice == '4':
            start = int(input("Start address (hex, e.g. 0001): "), 16)
            count = int(input("Number of registers: "))
            
            print(f"\nReading {count} registers starting at 0x{start:04X}")
            values = test_multi_register_read(port, start, count)
            
            if values:
                print("\nRaw values:")
                for i, v in enumerate(values):
                    print(f"  Register 0x{start+i:04X}: {v} (0x{v:04X})")
                    print(f"    Scaled 0.1: {v*0.1}")
                    print(f"    Scaled 0.01: {v*0.01}")
                    print(f"    Scaled 0.001: {v*0.001}")
            else:
                print("Failed to read")
                
        elif choice == '5':
            start = int(input("Start address (hex): "), 16)
            end = int(input("End address (hex): "), 16)
            scan_register_range(port, start, end)
            
        elif choice == 'q':
            break
    
    port.close()

if __name__ == "__main__":
    main()