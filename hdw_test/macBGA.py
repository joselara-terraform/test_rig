import serial
import time

def send(ser, cmd):
    ser.write((cmd + '\r\n').encode('ascii'))
    time.sleep(0.1)
    return ser.read_all().decode('ascii', errors='ignore').strip()

# Serial port for macOS
SERIAL_PORT = '/dev/tty.usbserial-B0035Q79'

try:
    ser = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    send(ser, "MSMD 1")                 # Binary gas mode
    send(ser, "GASP 7782-44-7")         # Primary gas: O2
    send(ser, "GASS 7727-37-9")         # Secondary gas: N2

    print("Temperature:", send(ser, "TCEL?"), "°C")
    print("Pressure:", send(ser, "PRES?"), "psi")
    print("Speed of Sound:", send(ser, "NSOS?"), "m/s")
    print("Primary Gas Concentration:", send(ser, "RATO? 1"), "%")

    ser.close()
except serial.SerialException as e:
    print("Failed to connect to serial port:", e)
