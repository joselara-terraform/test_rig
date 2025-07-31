#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2024-05-16 9:18

@author: peca
"""
from xc2.bus import SerialBus
from xc2.utils import discover_serial_ports, get_serial_from_port
from xc2.consts import ProtocolEnum
import asyncio

from xc2.xc2_dev_mis import XC2Mis


async def read_buffer(mis_dev: XC2Mis):
    while mis_dev.get_reading():
        await mis_dev.read_buffer_cmd()
        await asyncio.sleep(0)
    ret = await mis_dev.read_buffer()
    for dat in ret["data"]:
        print(dat)


async def main():
    my_ports = discover_serial_ports()
    port = my_ports[0]
    bus_sn = get_serial_from_port(port)
    print(my_ports)

    baud_rate = 1000_000
    adr_dec = 0xFFF

    # set XC2 bus
    my_bus = SerialBus(
        port=port,
        log_bytes=False,
        baud_rate=baud_rate,
        bus_sn=bus_sn,
        protocol_type=ProtocolEnum.XC2,
    )
    await my_bus.connect()
    my_device = XC2Mis(my_bus, adr_dec)
    echo = await my_device.get_echo()
    if not echo == 2:
        raise ConnectionError

    await my_device.gen_start(1, 1_000)
    await asyncio.sleep(1)
    await my_device.dac_offset(-10.0, -10.0)
    sample_rate = await my_device.acq_start_osci_by_periods()
    print(sample_rate)
    await read_buffer(my_device)
    await my_device.gen_stop()


if __name__ == "__main__":
    asyncio.run(main())
