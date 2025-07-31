#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 12:07:33 2023

@author: peca
"""
from xc2.bus import TCPBus
from xc2.consts import ProtocolEnum
import asyncio
from xc2.xc2_device import XC2Device
import sys
import re
import os
from xc2.consts import DeviceStatus, BusStatus


async def main(device: XC2Device, file_path: str, file_port: int = 8000):
    if not isinstance(device.bus, TCPBus):
        raise NotImplementedError("Uploading FPGA is possible only with TCP not serial")

    try:
        await device.write_reg_by_name(1, "fpga_control_arm")
    except Exception as e:
        raise e
    await asyncio.sleep(2)

    control_status = await device.read_and_get_reg_by_name("fpga_control_arm")
    if not control_status:
        raise ValueError("Unable to set FPGA control arm reg")
    writer = None
    reader = None
    buffer_size = 4096
    for _ in range(5):
        coro = asyncio.open_connection(device.bus.server_addr[0], file_port)
        try:
            reader, writer = await asyncio.wait_for(coro, timeout=3)
            break
        except asyncio.TimeoutError:
            writer = None
            reader = None
    if writer is None or reader is None:
        raise TimeoutError(f"Unable to connect to file server port {file_port}")

    print("Connected")
    filesize = os.path.getsize(file_path)
    print(f"file size: {filesize}")
    sent = 0
    try:
        with open(file_path, "rb") as f:
            while True:
                bytes_read = f.read(buffer_size)
                if not bytes_read:
                    break
                sent += buffer_size
                writer.write(bytes_read)
                await writer.drain()
                await asyncio.sleep(0)
                print(f"Sent: {sent} B {round((sent / filesize) * 100)}%")
    except Exception as e:
        try:
            await device.write_reg_by_name(0, "fpga_control_arm")
            print(f"sending not completed {e}")
            return 1
        except Exception as e:
            raise e
    print("sending completed")

    print("Waiting for FPGA")
    ready = False
    for i in range(10):
        control_status = await device.read_and_get_reg_by_name("fpga_control_arm")
        if not control_status:
            print("FPGA ready")
            ready = True
            break
        print(f"FPGA not ready for {i}s")
        await asyncio.sleep(1)

    if not ready:
        raise TimeoutError("FPGA load Failed")
    writer.close()


def handle_error():
    print(
        "Wrong parameters\n"
        "-i ip addr\n"
        "-p tcp port\n"
        "-s sending port\n"
        "-a xc2_addr\n"
        "-f file path\n\n"
        "All these parameters are mandatory\n"
        "-h or help for more information"
    )
    sys.exit(1)


async def prepare_and_run(parameters: dict):
    ip_addr = parameters["ip_addr"]
    port = parameters["port"]
    xc2_addr = parameters["xc2_addr"]
    file_path = parameters["file_path"]
    try:
        bus = TCPBus(ip_addr, port, ProtocolEnum.XC2)
        await bus.connect()
        bus.status = BusStatus.Available
        device = XC2Device(bus, xc2_addr, DeviceStatus.Firmware)
        await device.initial_structure_reading()
        file_port = await device.read_and_get_reg_by_name("tcp_fpga_flash_loader_port")
    except Exception as e:
        raise e
    await main(device, file_path, file_port)


if __name__ == "__main__":
    args = sys.argv[1:]
    ip_addr_m = None
    port_m = None
    xc2_addr_m = None
    file_path_m = None
    try:
        if not len(args) > 0:
            args.append("help")

        elif len(args) == 4 * 2:
            ip_re = re.compile(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}")
            ip_addr_m = args[args.index("-i") + 1]
            if not ip_re.match(ip_addr_m):
                print(f"{ip_addr_m} not an ip addr")
                raise ValueError
            port_m = int(args[args.index("-p") + 1])
            xc2_addr_m = int(args[args.index("-a") + 1], 0)
            file_path_m = args[args.index("-f") + 1]
            if not os.path.exists(file_path_m):
                print("File does not exists")
                raise ValueError

        elif len(args) == 1 or ("help" in args or "-h" in args):
            print(
                "Parameters for uploading fpga via TCP:\n"
                "-i ip addr\n"
                "-p tcp port\n"
                "-a xc2_addr\n"
                "-f file path\n\n"
                "All these parameters are mandatory\n"
                "-h or help shows this help\n"
                "example:\n"
                "python3 xc2_load_fpga.py -i 10.11.2.2 -p 17001 -a 0x2 -f /path/to/file.rpd"
            )
            sys.exit(0)
        else:
            raise ValueError
    except ValueError:
        handle_error()
    except KeyError:
        handle_error()
    except Exception as e:
        print(e)
        handle_error()

    if None in [ip_addr_m, port_m, xc2_addr_m, file_path_m]:
        handle_error()

    asyncio.run(
        prepare_and_run(
            {
                "ip_addr": ip_addr_m,
                "port": port_m,
                "xc2_addr": xc2_addr_m,
                "file_path": file_path_m,
            }
        )
    )
    sys.exit(0)
