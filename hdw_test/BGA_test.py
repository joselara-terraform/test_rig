import serial
import time

def send(ser, cmd):
    print(f"Sending: {cmd}")
    ser.write((cmd + '\r\n').encode('ascii'))
    time.sleep(0.1)
    response = ser.read_all().decode('ascii', errors='ignore').strip()
    print(f"Response: '{response}' ({len(response)} chars)")
    return response

def test_port(port, bga_name):
    print(f"\n=== Testing {bga_name} on {port} ===")
    
    try:
        # Connect to BGA244
        ser = serial.Serial(port, 9600, timeout=1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Test device identification first
        print("\n--- Device Identification ---")
        idn_response = send(ser, "*IDN?")

        # Set mode and gases (using BGA 1 configuration)
        print("\n--- Setting Mode and Gases ---")
        send(ser, "MSMD 1")                # Binary gas mode
        send(ser, "GASP 7782-44-7")        # Primary gas: O2
        send(ser, "GASS 1333-74-0")        # Secondary gas: H2

        # Read values
        print("\n--- Reading Measurements ---")
        print("Temperature:", send(ser, "TCEL?"), "°C")
        print("Pressure:", send(ser, "PRES?"), "psi")
        print("Speed of Sound:", send(ser, "NSOS?"), "m/s")
        print("Primary Gas Concentration:", send(ser, "RATO? 1"), "%")
        print("Secondary Gas Concentration:", send(ser, "RATO? 2"), "%")

        # Close connection
        ser.close()
        print(f"✅ {bga_name} test complete")
        
    except Exception as e:
        print(f"❌ Error testing {bga_name}: {e}")

if __name__ == "__main__":
    # Test all connected BGAs
    test_port("COM8", "BGA 1 (H2 Header)")
    test_port("COM9", "BGA 2 (O2 Header)") 
    # test_port("COM10", "BGA 3 (De-oxo)")  # Not connected yet
    
    print("\n=== All Tests Complete ===")
    print("Compare the outputs to see which BGA has issues")
