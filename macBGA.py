import serial
import time

def send(ser, cmd):
    ser.write((cmd + '\r\n').encode('ascii'))
    time.sleep(0.1)
    return ser.read_all().decode('ascii', errors='ignore').strip()

# Connect to BGA244
ser = serial.Serial('/dev/tty.usbserial-B003RK9Z', 9600, timeout=1)
ser.reset_input_buffer()
ser.reset_output_buffer()

# O2: 7782-44-7
# N2: 7727-37-9
# H2: 1333-74-0

# Set mode and gases
send(ser, "MSMD 1")                # Binary gas mode
send(ser, "GASP 7727-37-9")        # Primary gas: O2
send(ser, "GASS 7782-44-7")        # Secondary gas: N2

# Read values
print("Temperature:", send(ser, "TCEL?"), "°C")
print("Pressure:", send(ser, "PRES?"), "psi")
print("Speed of Sound:", send(ser, "NSOS?"), "m/s")
print("Primary Gas Concentration:", send(ser, "RATO? 1"), "%")

# Close connection
ser.close()