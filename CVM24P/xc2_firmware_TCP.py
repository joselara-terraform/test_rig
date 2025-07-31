#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 12:07:33 2023

@author: peca
"""
import os.path
import re
import sys

from xc2.bus import TCPBus
from xc2.consts import (
    ProtocolEnum,
    DeviceStatus,
    BusStatus,
    XC2Addr,
    XC2Commands,
    XC2SysSubcommands,
)
from xc2.xc2_except import XC2TimeoutError
import asyncio
import struct
from time import sleep
from xc2.xc2_device import XC2Device
from xc2.bus_utils import icmp_ping
from xc2.utils import intel_hex_to_bin


async def main(
    device: XC2Device,
    file_path: str,
    my_addr=XC2Addr.MASTER,
):
    in_bootloader = False

    print(f"{hex(device.addr)} -> Uploading: {file_path}")
    if file_path.endswith("bin"):
        with open(file_path, "rb") as fl:
            fl_content = fl.read()
            fl.close()
    elif file_path.endswith("hex"):
        fl_content = intel_hex_to_bin(file_path)

    else:
        raise TypeError("File type unsupported")

    try:
        ret = await device.bus.command(my_addr, device.addr, XC2Commands.CMD_ECHO)
        if int.from_bytes(ret, byteorder="big") == XC2SysSubcommands.ECHO_BOOT_LOADER:
            in_bootloader = True
    except Exception as e:
        raise e
    if int.from_bytes(ret, byteorder="big") == XC2SysSubcommands.ECHO_BOOT_LOADER:
        in_bootloader = True
    if not in_bootloader:
        print(f"{hex(device.addr)} -> Resetting Device")
        in_bootloader = False
        try:
            await device.reset_and_stay_in_bootloader()
        except Exception:
            raise ConnectionError("Unable to set stay in bootloader. Do it manually!")
        device.bus.close()
        ip, port = device.bus.server_addr
        protocol = device.bus.protocol
        new_bus = TCPBus(ip, port, protocol)
        sleep(1)
        for i in range(100):
            ret = icmp_ping(device.bus)
            if not ret:
                sleep(1)
                continue
            try:
                await new_bus.connect()
                device.bus = new_bus
                ret = await device.bus.command(my_addr, device.addr, XC2Commands.CMD_ECHO)
                if int.from_bytes(ret, byteorder="big") == XC2SysSubcommands.ECHO_BOOT_LOADER:
                    in_bootloader = True
                    break
            except TimeoutError:
                del new_bus
                new_bus = TCPBus(ip, port, protocol)
                sleep(1)
                continue
            except Exception as e:
                print(e)
                del new_bus
                new_bus = TCPBus(ip, port, protocol)
                sleep(1)
                continue
        if not in_bootloader:
            raise XC2TimeoutError(f"{hex(device.addr)} -> Bootloader can not be initialized")
        print(f"{hex(device.addr)} -> Device in Bootloader")
    # receiving page size
    page_size = await device.bus.command(
        my_addr,
        device.addr,
        XC2Commands.CMD_BLCMD,
        struct.pack("!B", XC2SysSubcommands.BL_GETBUFFSIZE),
    )
    page_size = int.from_bytes(page_size, byteorder="big")
    print(f"{hex(device.addr)} -> Page size:{page_size}")
    # reading bin file
    device.page_size = page_size
    sleep(0)

    # deviding bin into pages
    pages_count = len(fl_content) // page_size
    pages = [fl_content[i * page_size : (i + 1) * page_size] for i in range(pages_count)]
    # not full page appanding
    remaining_page = fl_content[pages_count * page_size :]
    if remaining_page != b"":
        pages.append(remaining_page)
    try:
        print(f"{hex(device.addr)} -> Total pages:{len(pages)}")
        # chunk size of binary file (data in xc2 packet without subcomands)
        device.pages_count = len(pages)
        device.page_index = 0
        device.firmware_loading = True
        sleep(0.1)
        chunk_size = 128
        buffer_offset = 0  # buffer offset on page
        for page_index in range(len(pages)):
            page = pages[page_index]
            device.page_index = page_index
            # deviding pages into chungs
            chunks_count = len(page) // chunk_size
            chunks = [page[i * chunk_size : (i + 1) * chunk_size] for i in range(chunks_count)]
            remaining_chunk = page[chunks_count * chunk_size :]
            # not full packet
            if remaining_chunk != b"":
                chunks.append(remaining_chunk)

            # packet sanding into device
            ind = 0
            for chunk in chunks:
                ind += 1
                byte_b_off = buffer_offset.to_bytes(2, byteorder="big")
                byte_bl_writebuf = struct.pack("!B", XC2SysSubcommands.BL_WRITEBUF)
                data = byte_bl_writebuf + byte_b_off + chunk
                ret = await device.bus.command(my_addr, device.addr, XC2Commands.CMD_BLCMD, data)

                buffer_offset += len(chunk)
            # writing page into flash
            data = struct.pack("!B", XC2SysSubcommands.BL_PROGFLASH) + page_index.to_bytes(2, byteorder="big")
            ret = await device.bus.command(my_addr, device.addr, XC2Commands.CMD_BLCMD, data, timeout=25000)
            print(f"{hex(device.addr)} -> Page sent:{page_index};{round((page_index / len(pages)) * 100)}%")
            sleep(0)
            buffer_offset = 0

        print(f"{hex(device.addr)} -> Writing firmware into flash")
        sleep(0)
        # Finish upload and calculate CRC
        try:
            await device.bus.command(
                my_addr,
                device.addr,
                XC2Commands.CMD_BLCMD,
                struct.pack("!B", XC2SysSubcommands.BL_APPLCRC),
                timeout=10000,
            )
        except XC2TimeoutError:
            pass

        # Waiting and reseting
        while True:
            try:
                await device.bus.command(my_addr, device.addr, XC2Commands.CMD_ECHO)
                break
            except XC2TimeoutError:
                sleep(0.1)
                continue

        print(f"{hex(device.addr)} -> Resetting Device")

        await device.reset()
        device.bus.close()
    except Exception as e:
        try:
            await device.reset()
            device.bus.close()
        except Exception:
            pass
        raise e


def handle_error():
    print("Wrong parameters\n-i ip addr\n-p tcp port\n-a xc2_addr\n-f file path\n\nAll these parameters are mandatory\n-h or help for more information")
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
    except Exception as e:
        raise e
    await main(device, file_path)


if __name__ == "__main__":
    args = sys.argv[1:]
    ip_addr_m = None
    port_m = None
    xc2_addr_m = None
    file_path_m = None
    try:
        if not len(args) > 0:
            args.append("help")

        if len(args) == 4 * 2:
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
                "Parameters for uploading firmware via TCP:\n"
                "-i ip addr\n"
                "-p tcp port\n"
                "-a xc2_addr\n"
                "-f file path\n\n"
                "All these parameters are mandatory\n"
                "-h or help shows this help\n"
                "example:\n"
                "python3 xc2_firmware_TCP.py -i 10.11.2.2 -p 17001 -a 0x2 -f /path/to/file.bin"
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
