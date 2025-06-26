import serial
import time
from collections import defaultdict

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

def decode_response(response):
    """Decode response based on observed patterns"""
    if len(response) < 5:
        return None
    
    result = {
        'raw': response.hex(),
        'length': len(response),
        'slave_id': response[0],
        'function': response[1],
        'byte_count': response[2]
    }
    
    # Standard Modbus responses
    if result['byte_count'] == 0x02 and len(response) >= 7:
        # Single register response
        value = (response[3] << 8) | response[4]
        result['type'] = 'standard_single'
        result['value'] = value
        result['voltage'] = value * 0.1
        
    elif result['byte_count'] == 0x08 and len(response) >= 13:
        # 4 register response
        result['type'] = 'standard_multi'
        result['voltage'] = ((response[3] << 8) | response[4]) * 0.1
        result['current'] = ((response[5] << 8) | response[6]) * 0.1
        result['power'] = ((response[7] << 8) | response[8]) * 0.1
        result['capacity'] = ((response[9] << 8) | response[10]) * 0.1
        
    elif result['byte_count'] == 0x09 and len(response) >= 8:
        # Non-standard format - appears frequently
        # Pattern observed: 01 03 09 XX XX YY YY ZZ
        result['type'] = 'custom_0x09'
        
        # Try different interpretations
        word1 = (response[3] << 8) | response[4] if len(response) > 4 else 0
        word2 = (response[5] << 8) | response[6] if len(response) > 6 else 0
        
        # Hypothesis 1: First word might be related to voltage
        # But values like 0x03A4 (932) seem too high for 0.1V units
        # Maybe it's in different units?
        
        # Hypothesis 2: Check if lower byte of first word matches voltage
        # 0x03A4 -> A4 = 164 -> 16.4V? Still too high
        
        # Hypothesis 3: Maybe the actual voltage is in a different position
        # Let's extract all possible interpretations
        result['word1'] = word1
        result['word2'] = word2
        result['byte3'] = response[3] if len(response) > 3 else 0
        result['byte4'] = response[4] if len(response) > 4 else 0
        result['byte5'] = response[5] if len(response) > 5 else 0
        result['byte6'] = response[6] if len(response) > 6 else 0
        
        # Try various scaling factors
        result['voltage_w1_0.1'] = word1 * 0.1
        result['voltage_w1_0.01'] = word1 * 0.01
        result['voltage_b3'] = response[3] * 0.1 if len(response) > 3 else 0
        result['voltage_b4'] = response[4] * 0.1 if len(response) > 4 else 0
        
    elif result['byte_count'] == 0x21 and len(response) >= 10:
        # 33 byte response - extended format
        result['type'] = 'custom_0x21'
        
        # Extract first few words
        words = []
        for i in range(3, min(13, len(response)-1), 2):
            if i+1 < len(response):
                word = (response[i] << 8) | response[i+1]
                words.append(word)
        
        result['words'] = words[:5]
        
        # Based on pattern, try to decode
        if len(words) >= 2:
            result['voltage_w0_0.1'] = words[0] * 0.1
            result['voltage_w0_0.01'] = words[0] * 0.01
            result['value_w1'] = words[1]
    
    return result

def find_voltage_pattern(responses):
    """Analyze responses to find which field contains voltage"""
    print("\nSearching for voltage field pattern...")
    print("Target voltage should be around 1.4V - 2.6V based on LCD")
    
    candidates = defaultdict(list)
    
    for resp in responses:
        decoded = decode_response(resp)
        if not decoded:
            continue
            
        # For standard responses, we know the voltage
        if decoded['type'] == 'standard_single':
            print(f"  Standard response voltage: {decoded['voltage']:.1f}V")
            
        elif decoded['type'] == 'standard_multi':
            print(f"  Standard multi voltage: {decoded['voltage']:.1f}V")
            
        elif decoded['type'] == 'custom_0x09':
            # Test each byte and word to see if it could be voltage
            tests = [
                ('byte3', decoded['byte3'] * 0.1),
                ('byte3_direct', decoded['byte3']),
                ('byte4', decoded['byte4'] * 0.1),
                ('byte4_direct', decoded['byte4']),
                ('byte5', decoded['byte5'] * 0.1),
                ('byte6', decoded['byte6'] * 0.1),
                ('word1_0.01', decoded['word1'] * 0.01),
                ('word1_0.001', decoded['word1'] * 0.001),
                ('word2_0.01', decoded['word2'] * 0.01),
                ('word2_0.001', decoded['word2'] * 0.001),
            ]
            
            for name, value in tests:
                if 0.5 <= value <= 5.0:  # Reasonable voltage range
                    candidates[name].append(value)

def main():
    port = serial.Serial(
        port='/dev/cu.usbserial-B0035Q79',
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=0.5
    )
    
    print("Custom Protocol Decoder for Charger")
    print("=" * 60)
    
    # Collect samples
    print("\nCollecting samples...")
    
    request = bytearray([0x01, 0x03, 0x00, 0x01, 0x00, 0x01])
    request += calculate_crc(request)
    
    responses = []
    response_types = defaultdict(int)
    
    for i in range(30):
        port.reset_input_buffer()
        port.write(request)
        time.sleep(0.05)
        
        response = port.read(256)
        if response:
            responses.append(response)
            decoded = decode_response(response)
            if decoded:
                response_types[decoded['type']] += 1
    
    print(f"\nCollected {len(responses)} responses")
    print("Response types:")
    for rtype, count in response_types.items():
        print(f"  {rtype}: {count}")
    
    # Analyze patterns
    find_voltage_pattern(responses)
    
    # Show detailed decoding of each type
    print("\n" + "=" * 60)
    print("Detailed decoding by type:")
    
    shown = set()
    for resp in responses:
        decoded = decode_response(resp)
        if decoded and decoded['raw'] not in shown:
            shown.add(decoded['raw'])
            
            print(f"\n{decoded['type']}:")
            print(f"  Raw: {decoded['raw']}")
            
            if decoded['type'] == 'standard_single':
                print(f"  Voltage: {decoded['voltage']:.1f}V")
                
            elif decoded['type'] == 'standard_multi':
                print(f"  Voltage: {decoded['voltage']:.1f}V")
                print(f"  Current: {decoded['current']:.1f}A")
                print(f"  Power: {decoded['power']:.1f}kW")
                print(f"  Capacity: {decoded['capacity']:.1f}kWh")
                
            elif decoded['type'] == 'custom_0x09':
                print(f"  Byte sequence: {decoded['byte3']:02X} {decoded['byte4']:02X} {decoded['byte5']:02X} {decoded['byte6']:02X}")
                print(f"  Possible voltages:")
                print(f"    - Byte 3 * 0.1: {decoded['byte3'] * 0.1:.1f}V")
                print(f"    - Byte 4 * 0.1: {decoded['byte4'] * 0.1:.1f}V")
                print(f"    - Word1 * 0.01: {decoded['word1'] * 0.01:.2f}V")
                print(f"    - Word1 * 0.001: {decoded['word1'] * 0.001:.3f}V")
                
            elif decoded['type'] == 'custom_0x21':
                print(f"  First 5 words: {decoded['words']}")
                if decoded['words']:
                    print(f"  Possible voltages:")
                    print(f"    - Word0 * 0.01: {decoded['words'][0] * 0.01:.2f}V")
                    print(f"    - Word0 * 0.001: {decoded['words'][0] * 0.001:.3f}V")
    
    # Find most consistent voltage candidates
    print("\n" + "=" * 60)
    print("Most consistent values in 0.5-5.0V range:")
    for name, values in candidates.items():
        if len(values) > 2:
            avg = sum(values) / len(values)
            print(f"  {name}: avg={avg:.2f}V, count={len(values)}, values={values[:5]}")
    
    port.close()

if __name__ == "__main__":
    main()