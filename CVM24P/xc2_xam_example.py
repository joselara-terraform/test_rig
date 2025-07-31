#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 12:07:33 2023

@author: peca
"""
from xc2.bus import SerialBus
from xc2.utils import discover_serial_ports, discover_devices

from xc2.xc2_dev_xam import XC2Xam

if __name__ == "__main__":
    my_ports = discover_serial_ports()
    print(my_ports)

    baud_rate = 115200
    adr_dec = 0xA5
    new_adr = 4

    # set XC2 bus
    my_bus = SerialBus(port=my_ports[0], log_bytes=False, baud_rate=baud_rate)
    # discover all devices on the bus
    my_devices = discover_devices(bus=my_bus)
    print(my_devices)

    # create XC2Xam object
    my_device = XC2Xam(my_bus, adr_dec)
    # my_device.get_app_status()

    my_device.send_app_readwrite(0, [1, 2, 3, 4, 5, 6])  # FIXME: this i a problem?
    print("stop")
