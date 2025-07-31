import logging
import struct

from icmplib import ping

# from .xc2_device import XC2Device
from .consts import (
    XC2Addr,
    XC2PacketType,
    XC2Commands,
    XC2SysSubcommands,
    BusStatus,
    DeviceStatus,
)

# from .bus import BusBase
from .packets import XC2Packet
from .xc2_except import UnexpectedAnswerError, XC2TimeoutError
import asyncio


async def get_serial(bus, dst_addr: int, my_addr=XC2Addr.MASTER) -> tuple:
    """Asynchronous function to get serial number of device on bus.

    :param bus: Bus object that inherits `bus.BusBase` class. Usually `bus.XC2Bus` class. Baud rate and port must be specified.
    :type bus: `bus.BusBase` or child class of `bus.BusBase`
    :param dst_addr: Address of device to get serial number from
    :type dst_addr: int
    :param my_addr: Address of master device (Your PC), defaults to XC2Addr.MASTER
    :type my_addr: int, optional
    :return: Device type and serial number
    :rtype: tuple(str, str)
    """
    response = await bus.sys_command(
        my_addr=my_addr,
        device_addr=dst_addr,
        subcommand=XC2SysSubcommands.SYS_GETSERIAL,
    )
    device_type = response[0:5].decode("ascii")
    device_serial = response[5:].hex()
    return device_type, device_serial


async def get_broadcast_echo(bus, my_addr=XC2Addr.MASTER) -> dict:
    """
    Sends a broadcast echo command to all devices on the bus and returns a dict of responding devices with data.

    :param bus: Bus object that inherits `bus.BusBase` class. Usually `bus.XC2Bus` class. Baud rate and port must be specified.
    :param my_addr: Address of master device (Your PC)
    :return: Dictionary with responding device addresses as keys and data (in bootloader -> 1 in application ->2)
    :rtype: dict
    """
    pkt = XC2Packet(
        pkt_type=XC2PacketType.COMMAND,
        dst=XC2Addr.BROADCAST,
        src=my_addr,
        cmd=XC2Commands.CMD_ECHO,
    )
    answers = await bus.broadcast_pkt(pkt)

    return dict([(answer.src, int.from_bytes(answer.data)) for answer in answers])


async def get_serial_broadcast(bus, my_addr=XC2Addr.MASTER) -> dict:
    """
    Sends a broadcast get serial command to all devices on the bus and returns a dict of responding devices with data.

    :param bus: Bus object that inherits `bus.BusBase` class. Usually `bus.XC2Bus` class. Baud rate and port must be specified.
    :param my_addr: Address of master device (Your PC)
    :return: Dictionary of devices with serial numbers. The key is the device address and the value is a dictionary with keys `dev_type` and `dev_serial`.
    :rtype: dict
    """
    pkt = XC2Packet(
        pkt_type=XC2PacketType.COMMAND,
        dst=XC2Addr.BROADCAST,
        src=my_addr,
        cmd=XC2Commands.CMD_SYS,
        data=struct.pack("!B", int(XC2SysSubcommands.SYS_GETSERIAL)),
    )
    answers = await bus.broadcast_pkt(pkt)

    ret_dict = {}

    for answer in answers:
        device_type = answer.data[0:5].decode("ascii")
        device_serial = answer.data[5:].hex()
        ret_dict[answer.src] = {
            "dev_type": device_type,
            "dev_serial": device_serial,
        }
    return ret_dict


async def get_feature_broadcast(bus, my_addr=XC2Addr.MASTER) -> dict:
    """
    Sends a broadcast get feature command to all devices on the bus and returns a dict of responding devices with data.

    :param bus: XC2Bus specify baud rate and port
    :param my_addr: Address of master device (Your PC)
    :return: Dictionary of devices with features. The key is the device address and the value
    is a dictionary with keys `id_product`, `id_vendor`, `id_version`, `id_custom_1` and `id_custom_2`.
    These keys contains values of corresponding device registers.
    :rtype: dict
    """
    pkt = XC2Packet(
        pkt_type=XC2PacketType.COMMAND,
        dst=XC2Addr.BROADCAST,
        src=my_addr,
        cmd=XC2Commands.CMD_GET_FEATURE,
    )
    answers = await bus.broadcast_pkt(pkt)

    ret_dict = {}

    for answer in answers:
        answer_raw_list = answer.data.split(b"\x00")
        data: list[str] = [feature.decode("ascii") for feature in answer_raw_list][:5]
        ret_dict[answer.src] = {
            "id_product": data[0],
            "id_vendor": data[1],
            "id_version": data[2],
            "id_custom_1": data[3],
            "id_custom_2": data[4],
        }

    return ret_dict


async def send_reset_broadcast(bus, my_addr=XC2Addr.MASTER) -> dict:
    """
    Sends a broadcast reset command to all devices on the bus and returns a dict of responding devices with data.
    This will reset all devices on the bus. TODO: <---Verify this!!

    :param bus: XC2Bus specify baud rate and port
    :param my_addr: Address of master device (Your PC)
    :return: Dictionary with responding device addresses as keys and data (in bootloader -> 1 in application ->2)
    """
    pkt = XC2Packet(
        pkt_type=XC2PacketType.COMMAND,
        dst=XC2Addr.BROADCAST,
        src=my_addr,
        cmd=XC2Commands.CMD_SYS,
        data=struct.pack("!B", int(XC2SysSubcommands.SYS_RESET)),
    )
    answers = await bus.broadcast_pkt(pkt)

    return dict([(answer.src, int.from_bytes(answer.data)) for answer in answers])


async def get_echo(bus, dst_addr: int, my_addr=XC2Addr.MASTER, timeout=None) -> int:
    """
    Sends an echo command to a specific device on the bus and returns the response.

    :param bus: Bus object that inherits `bus.BusBase` class. Usually `bus.XC2Bus` class.
    :param dst_addr: Address of echoing device
    :param my_addr: Address of master device (Your PC)
    :param timeout: Time in which device must answer.
    :return: Returns the data of the response if the device responded. Otherwise returns 0 and logs the error.
    :rtype: int
    """
    try:
        pkt = XC2Packet(
            pkt_type=XC2PacketType.COMMAND,
            dst=dst_addr,
            src=my_addr,
            cmd=XC2Commands.CMD_ECHO,
        )
        if timeout is None:
            timeout = bus.default_timeout
        answer = await bus.send_pkt_with_response(pkt, timeout=timeout)
    except Exception as e:
        logging.error(e)
        return 0
    return int.from_bytes(answer)


def icmp_ping(bus) -> bool:
    """Sends icmp ping to server address of bus and returns True if server is alive.

    :param bus: Bus object that inherits `bus.BusBase` class. Usually `bus.XC2Bus` class.
    :type bus: `bus.BusBase` or child class of `bus.BusBase`
    :return: True if server is alive, False if not
    :rtype: bool
    """
    try:
        host = ping(bus.server_addr[0], count=1, interval=1, timeout=1, privileged=False)
        if host.is_alive:
            return True
        else:
            return False
    except Exception as e:
        logging.exception(e)
        return False


async def stay_in_bootloader_with_command(device, my_addr=XC2Addr.MASTER, timeout=1000):
    """Sends a command to device to stay in bootloader mode. This is used to update the firmware of the device.

    :param device: Device object that inherits `xc2_device.XC2Device` class.
    :type device: `xc2_device.XC2Device` or child class of `xc2_device.XC2Device`
    :param my_addr: Address of master device (Your PC), defaults to XC2Addr.MASTER
    :type my_addr: int, optional
    :raises ConnectionError: Raised when the bus the device is on is not available
    :raises XC2TimeoutError: Raised when the device does not enter bootloader mode in 200 tries
    """
    if device.bus.status != BusStatus.Available:
        raise ConnectionError("Device bus not Available")
    in_bootloader = False
    try:
        await device.reset()
    except Exception as e:
        print(f"Device could not be reset. Do power reset:\n {e}")
    await asyncio.sleep(1)
    for i in range(int(timeout / 100)):
        try:
            await device.bus.command(my_addr, device.addr, XC2Commands.CMD_STAY_IN_BOOTLOADER)
            await asyncio.sleep(0)
            ret = await get_echo(device.bus, device.addr, my_addr)
            await asyncio.sleep(0)
            if ret == XC2SysSubcommands.ECHO_BOOT_LOADER:
                in_bootloader = True
                break
            elif ret == XC2SysSubcommands.ECHO_APPLICATION:
                in_bootloader = False
                break

        except XC2TimeoutError:
            await asyncio.sleep(0.1)
            continue
        except UnexpectedAnswerError:
            await asyncio.sleep(0.1)
            continue

    if not in_bootloader:
        raise XC2TimeoutError(f"{hex(device.addr)} -> Bootloader can not be initialized")
    device.stay_in_bootloader = True
    device.status = DeviceStatus.Resetting
