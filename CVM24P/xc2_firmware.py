#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 12:07:33 2023

@author: peca
"""
import struct
from xc2.bus import SerialBus
from xc2.utils import intel_hex_to_bin
import asyncio
import sys
import os
from xc2.xc2_device import XC2Device
from xc2.consts import (
    XC2Addr,
    ProtocolEnum,
    XC2Commands,
    XC2SysSubcommands,
    BusStatus,
    DeviceStatus,
)
from xc2.xc2_except import XC2TimeoutError, UnexpectedAnswerError


async def main(device: XC2Device, file_path: str, my_addr=XC2Addr.MASTER):
    print(f"{hex(device.addr)} -> Uploading:{file_path}")
    in_bootloader = False
    try:
        ret = device.bus.command(my_addr, device.addr, XC2Commands.CMD_ECHO)
        if int.from_bytes(ret, byteorder="big") == XC2SysSubcommands.ECHO_BOOT_LOADER:
            in_bootloader = True
    except Exception as e:
        print(e)
    if not in_bootloader:
        print(f"{hex(device.addr)} -> Resetting Device")
        try:
            await device.reset()
        except Exception as e:
            print(f"Device could not be resetted. Do power reset:\n {e}")
        await asyncio.sleep(1)
        for i in range(100):
            try:
                await device.bus.command(my_addr, device.addr, XC2Commands.CMD_STAY_IN_BOOTLOADER)
                ret = device.bus.command(my_addr, device.addr, XC2Commands.CMD_ECHO)
                if int.from_bytes(ret, byteorder="big") == XC2SysSubcommands.ECHO_BOOT_LOADER:
                    in_bootloader = True
                    break
            except XC2TimeoutError:
                await asyncio.sleep(0.1)
                continue
            except UnexpectedAnswerError:
                await asyncio.sleep(0.1)
                continue
        if not in_bootloader:
            raise XC2TimeoutError(f"{hex(device.addr)} -> Bootloader can not be initialized")
    print(f"{hex(device.addr)} -> Device in Bootloader")
    # receiving page size
    page_size = device.bus.command(
        my_addr,
        device.addr,
        XC2Commands.CMD_BLCMD,
        struct.pack("!B", XC2SysSubcommands.BL_GETBUFFSIZE),
    )
    page_size = int.from_bytes(page_size, byteorder="big")
    print(f"Page size: {page_size}")
    # reading bin file
    device.page_size = page_size
    await asyncio.sleep(0)
    if file_path.endswith("bin"):
        with open(file_path, "rb") as fl:
            fl_content = fl.read()
            fl.close()
    elif file_path.endswith("hex"):
        fl_content = intel_hex_to_bin(file_path)

    else:
        raise TypeError("File type unsupported")

    # deviding bin into pages
    pages_count = len(fl_content) // page_size
    pages = [fl_content[i * page_size : (i + 1) * page_size] for i in range(pages_count)]
    # not full page appanding
    remaining_page = fl_content[pages_count * page_size :]
    if remaining_page != b"":
        pages.append(remaining_page)

    print(f"Total pages: {len(pages)}")
    # chunk size of binary file (data in xc2 packet without subcomands)
    device.pages_count = len(pages)
    device.page_index = 0
    device.firmware_loading = True
    await asyncio.sleep(0.1)
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
        for chunk in chunks:
            byte_b_off = buffer_offset.to_bytes(2, byteorder="big")
            byte_bl_writebuf = struct.pack("!B", XC2SysSubcommands.BL_WRITEBUF)
            data = byte_bl_writebuf + byte_b_off + chunk
            ret = device.bus.command(my_addr, device.addr, XC2Commands.CMD_BLCMD, data)

            buffer_offset += len(chunk)
        # writing page into flash
        data = struct.pack("!B", XC2SysSubcommands.BL_PROGFLASH) + page_index.to_bytes(2, byteorder="big")
        ret = device.bus.command(my_addr, device.addr, XC2Commands.CMD_BLCMD, data, timeout=25000)
        print(f"{hex(device.addr)} -> Page sent: {page_index} {round((page_index / len(pages)) * 100)}%")
        await asyncio.sleep(0)
        buffer_offset = 0

    print(f"{hex(device.addr)} -> Writing firmware into flash")
    await asyncio.sleep(0)
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
            await asyncio.sleep(0.1)
            continue
    try:
        await device.read_full_regs_structure()
        await device.read_and_get_full_regs()
        crc = hex(device.get_reg_by_name("applCRC")).upper().replace("X", "x")
    except Exception as e:
        print(f"Error reading CRC:{e}")
        crc = "ERROR"
    print(f"{hex(device.addr)} -> loaded_CRC:{crc}")
    print(f"{hex(device.addr)} -> Resetting Device")
    print(f"{hex(device.addr)} -> DONE")
    await device.reset()


def handle_error():
    print("Wrong parameters\n-p port\n-b baud_rate\n-a xc2_addr\n-f file path\n\nAll these parameters are mandatory\n-h or help for more information")
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    baud_rate_m = None
    port_m = None
    xc2_addr_m = None
    file_path_m = None
    try:
        if not len(args) > 0:
            file_path_m = "Y:/dev/MegaEIS/fw/EVM + Core/2023-08-21-trigger_synchronize/EVM8_0.0.357.bin"
            xc2_addr_m = 0x11
            port_m = "COM10"
            baud_rate_m = 1000000

        elif len(args) == 4 * 2:
            baud_rate_m = args[args.index("-b") + 1]
            port_m = int(args[args.index("-p") + 1])
            xc2_addr_m = int(args[args.index("-a") + 1], 0)
            file_path_m = args[args.index("-f") + 1]
            if not os.path.exists(file_path_m):
                print("File does not exists")
                raise ValueError

        elif len(args) == 1 or ("help" in args or "-h" in args):
            print(
                "Parameters for uploading firmware via TCP:\n"
                "-p port\n"
                "-b baud rate\n"
                "-a xc2_addr\n"
                "-f file path\n\n"
                "All these parameters are mandatory\n"
                "-h or help shows this help\n"
                "example:\n"
                "python3 xc2_firmware.py -p COM2 -b 115200 -a 0x2 -f /path/to/file.bin"
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

    if None in [baud_rate_m, port_m, xc2_addr_m, file_path_m]:
        handle_error()

    try:
        bus = SerialBus("UNDEFINED_SN", baud_rate_m, ProtocolEnum.XC2)
        bus.port = port_m
        bus.connect()
        bus.status = BusStatus.Available
        device_m = XC2Device(bus, xc2_addr_m, DeviceStatus.Firmware)
    except Exception as e:
        raise e
    asyncio.run(main(device_m, file_path_m))
    sys.exit(0)
