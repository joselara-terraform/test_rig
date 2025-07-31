import binascii
import crcmod
import platform
import re
import logging
import serial
import struct
from typing import Union
from .consts import ProtocolEnum, XCTRecordChannel
from icmplib import ping
import serial.tools.list_ports as list_ports
import string


def calc_xc2_crc(buf: bytes) -> int:
    """Calculate CRC-CCIT (CRC16/XMODEM) from buffer,

    :param buf: Buffer to calculate CRC from
    :type buf: bytes
    :return: CRC-CCIT (CRC16/XMODEM)
    :rtype: int
    """
    return binascii.crc_hqx(buf, 0)


def calc_modbus_crc(data: bytes) -> bytes:
    """Calculate crc16 using modbus standard (CRC-16-IBM)

    :param data: data to calculate crc from
    :type data: bytes
    :return: CRC-16-IBM
    :rtype: bytes
    """
    crc16 = crcmod.predefined.mkCrcFun("modbus")
    calculated_crc = crc16(data)
    final_crc = struct.pack("H", calculated_crc)
    return final_crc


def pretty_string_bytes(bytes_to_convert: bytes) -> str:
    """Convert bytes to string of hex numbers separated by space

    :param bytes: bytes to convert
    :type bytes: bytes
    :return: string of hex numbers separated by space
    :rtype: str
    """

    hexstr = bytes_to_convert.hex()
    return " ".join(hexstr[i : i + 2] for i in range(0, len(hexstr), 2))


def get_serial_from_port(port: str) -> str:
    """Get serial number of Kolibrik.net device from port name.

    :param port: port name (i. e. COM1, /dev/ttyUSB0)
    :type port: str
    :return: serial number
    :rtype: str
    """
    list_of_serial_ports = serial.tools.list_ports.comports()
    # Different naming schemes in Unix and Windows
    az_chars = string.ascii_uppercase
    if platform.system() == "Linux" or platform.system() == "Darwin":
        serial_num_re = re.compile(r"SER=(\S*)")
        loc_re = re.compile(r"LOCATION=.*")
        for p in list_of_serial_ports:
            loc_num = re.search(loc_re, p.hwid)
            if loc_num:
                loc_num = az_chars[int(loc_num.group(0)[-1])]
            else:
                loc_num = ""
            match = re.search(serial_num_re, p.hwid)
            if match and (p.device == port):
                return match.group(1) + loc_num
    else:
        serial_num_re = re.compile(r"SER=(\S*)[A-Z]?")
        for p in list_of_serial_ports:
            match = re.search(serial_num_re, p.hwid)
            if match and (p.device == port):
                return match.group(1)

    return ""


def get_serial_number() -> list:
    """Get list of serial numbers of all Kolibrik.net devices connected to PC.

    :return: list of serial numbers
    :rtype: list
    """
    list_of_serial_ports = serial.tools.list_ports.comports()
    # Different naming schemes in Unix and Windows
    match_list = []
    az_chars = string.ascii_uppercase
    if platform.system() == "Linux" or platform.system() == "Darwin":
        serial_num_re = re.compile(r"SER=(\S*)")
        loc_re = re.compile(r"LOCATION=.*")
        for p in list_of_serial_ports:
            loc_num = re.search(loc_re, p.hwid)
            if loc_num:
                loc_num = az_chars[int(loc_num.group(0)[-1])]
            else:
                loc_num = ""
            match = re.search(serial_num_re, p.hwid)
            if match:
                match_list.append(f"{match.group(1)+loc_num} ({p.device})")
    else:
        serial_num_re = re.compile(r"SER=(\S*)[A-Z]?")
        for p in list_of_serial_ports:
            match = re.search(serial_num_re, p.hwid)
            if match:
                match_list.append(f"{match.group(1)} ({p.device})")

    return match_list


def icmp_ping(dst: string) -> bool:
    """Ping device using ICMP protocol. Returns True if device is alive, False otherwise.
    Returns false if exception is raised.

    :param dst: IP address of device
    :type dst: str
    :return: True if device is alive, False otherwise. Returns false if exception is raised.
    :rtype: bool
    """
    try:
        host = ping(dst, count=1, interval=1, timeout=1, privileged=False)
        if host.is_alive:
            return True
        else:
            return False
    except Exception as e:
        logging.exception(e)
        return False


def discover_serial_ports(return_all: bool = False) -> list[str]:
    """
    Find all serial ports with probable xc2 communication
    returns list of port names which can be used in XC2Bus constructor

    :param return_all: Skip manufacturer and serial_number filtering.
    :return: list of ports ["COM1",...] / ["/dev/ttyUSB0", ...]
    """

    serial_port_list = list_ports.comports()
    if return_all:
        return [p.device for p in serial_port_list]
    testport_names = [
        p.device
        for p in serial_port_list
        if p.manufacturer == "STMicroelectronics"
        or (
            p.serial_number is not None
            and (
                p.serial_number[0:2] == "PW"  # KMS-PWR
                or p.serial_number[0:2] == "XU"  # XCGU
                or p.serial_number[0:2] == "KP"  # PTC
                or p.serial_number[0:2] == "CB"  # xADDA connection board
                or p.serial_number[0:2] == "MM"  # MB-Mini
                or p.serial_number[0:2] == "TV"  # Tevomet
                or p.serial_number[0:2] == "PP"  # PicoPotentiostat
                or p.serial_number[0:2] == "SR"  # KMS-SER
                or p.serial_number[0:2] == "A5"  # MIS tool
            )
        )
    ]
    return testport_names


def find_serial_ports(usb_serial: str) -> str:
    """
    Return serial port with specified usb serial number
    PROBABLY OBSOLETE, BECAUSE IT CAN FIND ONLY ONE PORT, USE `xc2_device.discover_serial_ports()` INSTEAD!!

    :param usb_serial: usb serial number of device
    :return: str
    """
    serial_port_list = list_ports.comports()
    for port in serial_port_list:
        if port.serial_number and usb_serial in port.serial_number:
            return port.device
    return ""


# def discover_device_addresses(bus: SerialBus, my_addr=XC2Addr.MASTER) -> list[int]:
#     """
#     Returns all devices addresses on the bus with current baud rate
#
#     :param bus: XC2Bus specify baud rate and port
#     :param my_addr: Address of master device (Your PC)
#     :return: list of device addresses
#     """
#     pkt = XC2Packet(
#         pkt_type=XC2PacketType.COMMAND,
#         dst=XC2Addr.BROADCAST,
#         src=my_addr,
#         cmd=XC2Commands.CMD_ECHO,
#     )
#     answers = bus.protocol.broadcast(pkt)
#     return [answer.src for answer in answers]
#
#
# def discover_devices(
#     bus: SerialBus, my_addr=XC2Addr.MASTER
# ) -> typing.Dict[int, typing.Tuple[str, str]]:
#     """
#     Returns all devices addresses on the bus with current baud rate
#
#     :param bus: XC2Bus specify baud rate and port
#     :param my_addr: Address of master device (Your PC)
#     :return: Dict of devices: { address : {"type":device_type, "sn":device_serial,"s_port":bus.port,"ttl":0} }
#     """
#     addrs = discover_device_addresses(bus, my_addr)
#     devices = {}
#     for addr in addrs:
#         serial_num_bytes = bus.protocol.sys_command(
#             my_addr, addr, XC2SysSubcommands.SYS_GETSERIAL
#         )
#         device_type = serial_num_bytes[0:5].decode("ascii")
#         device_serial = serial_num_bytes[5:].hex()
#         devices[addr] = {
#             "type": device_type,
#             "sn": device_serial,
#             "s_port": bus.port,
#             "ttl": 0,
#         }
#     return devices


def intel_hex_to_bin(hex_file: str) -> bytes:
    """Convert Intel HEX file to binary. Used when flashing new firmware to device.

    :param hex_file: Path to Intel HEX file to convert to binary
    :type hex_file: str
    :return: Binary data
    :rtype: bytes
    """
    result = bytes()
    with open(hex_file, "rb") as f:
        data = f.read()
        f.close()

    n = 0
    adrSeg = 0
    adrExt = 0
    i = 0
    lines = data.splitlines()
    while i < len(lines):
        s = lines[i].decode("ascii").lower()
        len_s = len(s)
        if len_s < 11 or len_s % 2 == 0 or s[0] != ":":
            return result
        len_s = (len_s - 1) // 2
        buf = binascii.unhexlify(s[1:].encode("ascii"))
        if len(buf) != len_s:
            return result

        cnt = buf[0]
        adrH = buf[1]
        adrL = buf[2]
        typ = buf[3]

        if typ == 0:
            adr = adrExt + adrSeg + adrH * 256 + adrL
            n = max(n, adr + cnt)
            j = len(result)
            if n > j:
                result += b"\xff" * (n - j)
            result = result[:adr] + buf[4 : 4 + cnt] + result[adr + cnt :]
        elif typ == 1:
            break
        elif typ == 2:
            adrSeg = 16 * (buf[4] * 256 + buf[5])
        elif typ == 4:
            adrExt = 65536 * buf[5]

        i += 1

    result = result[:n]

    return result


def str_to_int(dec_str: str) -> int:
    """Convert string to int. If string starts with 0x, it is considered as hexadecimal number.

    :param dec_str: String to convert to int
    :type dec_str: str
    :raises ValueError: Raised when string is only "0x" or empty string)
    :return: Converted string
    :rtype: int
    """
    if dec_str[:2] == "0x":
        if len(dec_str) >= 3:
            xc2_int = int(dec_str, 16)
        else:
            raise ValueError("Wrong hexadecimal string")
    elif dec_str == "":
        raise ValueError("Empty hexadecimal string")
    else:
        xc2_int = int(dec_str)
    return xc2_int


def parse_dev_id(dev_id: str, ret_addr_as_str=False) -> tuple[ProtocolEnum, str, int | str]:
    """Parse device id string to protocol, bus and XC2 address

    :param dev_id: device id string
    :type dev_id: str
    :param ret_addr_as_str: If True, XC2 address is returned as string, otherwise
    it is returned as int, defaults to False
    :type ret_addr_as_str: bool, optional
    :raises NotImplementedError: Raised when the protocol specified in the dev_id string is not implemented
    :raises ValueError: Raised when the dev_id string is not in format <protocol>://<bus>/<xc2_addr>
    :return: Parsed device id into specified parts
    :rtype: tuple[ProtocolEnum, str, int | str]
    """
    match = re.match(r"(\w+):\/\/([\w\.:\s*]+)\/(\w+)", dev_id)
    if match:
        protocol = match.group(1).lower()
        if protocol == "xc2":
            protocol = ProtocolEnum.XC2
        elif protocol == "modbus":
            protocol = ProtocolEnum.Modbus
        elif protocol == "xct":
            protocol = ProtocolEnum.XCT
        else:
            raise NotImplementedError(f"No such protocol implemented ({protocol})")
        bus = match.group(2)
        xc2_addr = match.group(3).lower()
    else:
        raise ValueError("dev_id is not in format protocol://bus/<xc2_addr>")
    if not ret_addr_as_str:
        if "x" in xc2_addr:
            xc2_addr = int(xc2_addr, 16)
        else:
            xc2_addr = int(xc2_addr)
    return protocol, bus, xc2_addr


def create_dev_id(protocol: Union[str, ProtocolEnum], bus: str, xc2_addr: int) -> str:
    """Create device id string from protocol, bus and XC2 address.

    :param protocol: Specifies the protocol used for communication with device.
    Can be either string or `xc2.consts.ProtocolEnum`.
    :type protocol: Union[str, ProtocolEnum]
    :param bus: Specifies the bus used for communication with device.
    :type bus: str
    :param xc2_addr: XC2 address of device. It is implicitly converted to hexadecimal number.
    :type xc2_addr: int
    :raises ValueError: Raised when xc2_addr is not a number.
    :return: Device id string in format <protocol>://<bus>/<xc2_addr>
    :rtype: str
    """
    try:
        xc2_addr = hex(int(xc2_addr))
    except ValueError:
        raise ValueError("xc2_addr is not a number.")
    xc2_addr = xc2_addr[xc2_addr.find("x") + 1 :]
    xc2_addr = "0x" + "0" * (3 - len(xc2_addr)) + xc2_addr
    if isinstance(protocol, ProtocolEnum):
        protocol = str(protocol)

    return f"{protocol}://{bus}/{xc2_addr}"


def check_dev_id_format(dev_id: str) -> bool:
    """Check if device id string is in format <protocol>://<bus>/<xc2_addr>

    :param dev_id: Device id string
    :type dev_id: str
    :return: True if device id string is in format <protocol>://<bus>/<xc2_addr>, False otherwise
    :rtype: bool
    """
    try:
        parse_dev_id(dev_id)
        return True
    except NotImplementedError:
        return False
    except ValueError:
        return False


def bytes_to_int48(data: bytes, switch_order=0):
    """Convert 8 bytes to 48 bit integer. The results consists of 6 bytes int and created by combining
    all 8 bytes. Last two bits of each byte in data are ignored.

    :param data: 8 bytes to convert
    :type data: bytes
    :param switch_order: data[4] is taken as first byte when True, otherwise data[0] is first, defaults to 0
    :type switch_order: int, optional
    :raises ValueError: Raised when data is not 8 bytes long
    :return: 48 bit integer
    :rtype: int
    """
    # Získání jednotlivých bytů z bytového řetězce
    if len(data) != 8:
        raise ValueError("8 Bytes are needed to  convert bytes to int48")
    if not switch_order:
        byte1 = data[0]
        byte2 = data[1]
        byte3 = data[2]
        byte4 = data[3]
        byte5 = data[4]
        byte6 = data[5]
        byte7 = data[6]
        byte8 = data[7]
    else:
        byte1 = data[4]
        byte2 = data[5]
        byte3 = data[6]
        byte4 = data[7]
        byte5 = data[0]
        byte6 = data[1]
        byte7 = data[2]
        byte8 = data[3]

    # Konverze na záporné celé číslo s použitím dvojkového doplňkového kódu

    num = byte1 << 40 | byte2 << 40 - 6 | byte3 << 40 - 12 | byte4 << 40 - 18 | byte5 << 40 - 24 | byte6 << 40 - 30 | byte7 << 40 - 36 | byte8 << 42 - 40

    return num


def record_channel_mask_to_list(mask: int) -> list:
    ret = []
    if mask & XCTRecordChannel.Vout:
        ret.append(XCTRecordChannel.Vout.name)
    if mask & XCTRecordChannel.Vsense:
        ret.append(XCTRecordChannel.Vsense.name)
    if mask & XCTRecordChannel.Vref:
        ret.append(XCTRecordChannel.Vref.name)
    if mask & XCTRecordChannel.I:
        ret.append(XCTRecordChannel.I.name)

    return ret
