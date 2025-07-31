# Warning To run this demo. This file has to be in parent folder.
# Version 1.21

import asyncio

from xc2.bus import SerialBus
from xc2.bus_utils import get_broadcast_echo
from xc2.consts import ProtocolEnum
from xc2.utils import discover_serial_ports, get_serial_from_port
from xc2.xc2_dev_cvm64h import XC2Cvm64h


async def main():
    # Communication settings
    baud_rate = 1000000
    cvm64h_address = 0xA6

    # Establish connection with COM port
    my_ports = discover_serial_ports()
    bus_sn = get_serial_from_port(my_ports[0])
    print(my_ports)
    my_bus = SerialBus(bus_sn, port=my_ports[0], baud_rate=baud_rate, protocol_type=ProtocolEnum.XC2)
    await my_bus.connect()

    # Scan for all the devices on the bus
    my_devices = await get_broadcast_echo(bus=my_bus)
    print(f"Device list: {my_devices}")

    # Creating an instance of CVM24P device
    my_device = XC2Cvm64h(my_bus, cvm64h_address)

    # Reading structure of the regitry
    await my_device.initial_structure_reading()

    # Get app status variables: the fastest way to get channel voltages
    # await my_device.get_app_status()
    # print(f"Timestamp: {my_device.timestamp}")
    # print(f"Voltage sum: {my_device.ch_sum}")
    # print(f"Channel voltages: {my_device.v_channels}")

    # start = 8
    index = 10
    # stop = 10
    # Read register means refresh the structure of the CVM24P object with new value
    # await my_device.read_regs_range(start=start, stop=stop)
    # Get register means get corresponding value from the CVM24P object.
    # print(f"Register with index {index}: {my_device.get_reg_by_index(index)}")
    
    # Read and get register means read and immediately get this value
    print(await my_device.read_and_get_reg(index))

    # Write register
    await my_device.write_reg(data="Hello there", index=index)

    # Store current settings to device memory. To save the settings after reboot.
    await my_device.store_regs()

    await my_device.read_reg_by_name("ch_avg_V")
    print(await my_device.get_reg_by_name("ch_avg_V"))  # averaged channels values

    print(await my_device.read_and_get_reg_by_name("ch_V"))  # current channels values


if __name__ == "__main__":
    asyncio.run(main())
