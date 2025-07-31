# Warning To run this demo. This file has to be in parent folder.

import time
import timeit
import asyncio

from xc2.bus import SerialBus
from xc2.utils import discover_serial_ports, get_serial_from_port
from xc2.bus_utils import get_broadcast_echo
from xc2.consts import ProtocolEnum

from xc2.xc2_dev_cvm24p import XC2Cvm24p
from xc2.xc2_dev_cvm32a import XC2Cvm32a

CVM32_TEST = False
CVM24_TEST = True
LOG_CVM32A = False

SET_DEVICE_ADDRESS = False
SET_REGISTRY = False


async def main():
    my_ports = discover_serial_ports()
    bus_sn = get_serial_from_port(my_ports[0])
    print(my_ports)
    baud_rate = 1000000
    my_bus = SerialBus(bus_sn, port=my_ports[0], baud_rate=baud_rate, protocol_type=ProtocolEnum.XC2)
    await my_bus.connect()

    if CVM32_TEST:
        adr_dec = 3
        new_adr = 4
        # set XC2 bus

        # discover all devices on the bus
        my_devices = await get_broadcast_echo(bus=my_bus)
        print(my_devices)

        # create XC2Cvm32a object
        my_device = XC2Cvm32a(my_bus, adr_dec)

        # Get some status vars
        await my_device.get_app_status()
        print(my_device.t_cpu)
        print(my_device.v_cpu)
        print(my_device.v_channel)

        # Some commands
        print(my_device.get_echo())  # get device echo
        await my_device.reset()  # restart device
        time.sleep(2)  # wait till device is restarted

        if SET_DEVICE_ADDRESS:
            # Set device address
            await my_device.write_address(new_adr)  # set device address
            await asyncio.sleep(2)
            print(await get_broadcast_echo(bus=my_bus))
            await asyncio.sleep(3)
            my_device = XC2Cvm32a(my_bus, new_adr)  # create object with new address
            await asyncio.sleep(2)
            await my_device.write_address(adr_dec)  # set previous address
            print(await get_broadcast_echo(bus=my_bus))
            my_device = XC2Cvm32a(my_bus, adr_dec)  # create device with previous address
            print(my_device.read_serial_number())
            # print(my_device.get_feature())

        if SET_REGISTRY:
            # read registry
            start = 0
            index = 10
            stop = 36
            time.sleep(5)

            # Read and write registry
            await my_device.read_regs_range(start=start, stop=stop)
            my_device.print_all_regs_value()

            # set registry
            print(my_device.get_reg_by_index(index))
            await my_device.write_reg(data="Hello there", index=index)
            await my_device.read_regs_range(start=start, stop=stop)
            print(my_device.get_reg_by_index(index))

    elif CVM24_TEST:
        adr_dec = 0xFFF
        # new_address = 3180
        my_devices = await get_broadcast_echo(bus=my_bus)
        print(my_devices)
        my_device = XC2Cvm24p(my_bus, adr_dec)
        await my_device.initial_structure_reading()

        # Get app status vars
        await my_device.get_app_status()
        print(my_device.timestamp)
        print(my_device.ch_sum)
        print(my_device.v_channels)

        start = 8
        index = 10
        stop = 10

        # Read write store and restore regs
        await my_device.read_regs_range(start=start, stop=stop)
        print(my_device.get_reg_by_index(index))
        await my_device.write_reg(data="Hello there", index=index)
        await my_device.read_regs_range(start=start, stop=stop)
        print(my_device.get_reg_by_index(index))

        await my_device.store_regs()

        await asyncio.sleep(2)
        await my_device.read_regs_range(start=start, stop=stop)
        print(my_device.get_reg_by_index(index))

        await my_device.write_reg(data="Nazdar", index=index)
        await my_device.read_regs_range(start=start, stop=stop)
        print(my_device.get_reg_by_index(index))

        await my_device.restore_regs()

        await asyncio.sleep(2)
        await my_device.read_regs_range(start=start, stop=stop)
        print(my_device.get_reg_by_index(index))

        start = timeit.default_timer()
        await my_device.read_regs_range(start=0, stop=0)
        stop = timeit.default_timer()
        print(stop - start)

        # Some commands
        print(await my_device.get_echo())
        # await my_device.reset()
        # await asyncio.sleep(2)
        # await my_device.initial_structure_reading()
        # Chanage device adress
        # print(my_device.write_address(new_address))
        # print(await get_broadcast_echo(bus=my_bus))
        # my_device = XC2Cvm24p(my_bus, new_address)
        # print(my_device.write_address(adr_dec))
        # my_device = XC2Cvm24p(my_bus, adr_dec)
        # print(await get_broadcast_echo(bus=my_bus))
        # print(my_device.read_serial_number())
        # print(my_device.read_feature())
    else:
        adr_dec = 3
        reg_name = "ID_product"  # ID_product

        my_devices = await get_broadcast_echo(bus=my_bus)
        print(my_devices)

        my_device = XC2Cvm32a(my_bus, adr_dec)
        my_device.print_full_regs_structure()
        print(await my_device.read_reg_by_name(reg_name))
        print(await my_device.get_reg_by_name(reg_name))
        my_device.print_all_regs_value()


if __name__ == "__main__":
    asyncio.run(main())
