from dataclasses import dataclass
import struct

from .xc2_except import IncompletePacket, BadCrc
from .utils import calc_xc2_crc, calc_modbus_crc
from .consts import XC2ModbusFceCode, XC2PacketType, XC2Commands, XC2Flags, XCTPacketType, XC2Addr, XCTCommands


@dataclass(init=False)
class XC2Packet:
    """XC2Packet class defining the structure of the packet. It is used for
    creating and parsing packets.

    The packet has the following structure:
        - TYPE - 4 bits - Specifies the type of the packet (80 - Command, C0 - answer, 40 - event etc.)
        - DST - 12 bits - Destination address (0x001 - 0xFFF, 0x000 - Broadcast)
        - FLAGS - 4 bits - Specifies additional flags (0x80 - multicast, 0x40 - suppress answer etc.)
        - SRC - 12 bits - Source address (0x001 - 0xFFF, 0x000 - Broadcast)
        - LEN - 8 bits- Length of the packet without CRC (minimum 6 bytes)
        - CMD - 8 bits - Command (0x00 - 0xFF)
        - DATA - 0 - 246 bytes - Data
        - CRC - 16 bits - AVR CRC-16-CCITT (x^16 + x^12 + x^5 + 1) of the packet without CRC

    For further info see the documentation of the XC2 protocol.
    """

    pktype: int
    dst: int
    src: int
    cmd: int
    data: bytes
    flags: int  # = 0x0
    length: int  # = 6  #minimum packet length is 6 bytes

    def __init__(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags: XC2Flags = 0x0):
        """Constructor method. It is used to create XC2Packet instance.

        :param pkt_type: Value from :class:`xc2.consts.XC2PacketType` enum
        :type pkt_type: int | XC2PacketType
        :param dst: Destination address in 0xXXX format
        :type dst: hexadecimal
        :param src: Source address in 0xXXX format (0x001 for master)
        :type src: hexadecimal
        :param cmd: Command from :class:`xc2.consts.XC2Commands` enum
        :type cmd: int | XC2Commands
        :param data: Data to be packed into the packet, defaults to bytes([])
        :type data: bytes, optional
        :param flags: Flags from the :class:`xc2.consts.XC2Flags` enum (multicast, supress answer etc.), defaults to 0x0 (No flag)
        :type flags: hexadecimal, optional
        """
        self.pktype = pkt_type
        self.dst = dst
        self.src = src
        self.cmd = cmd
        self.data = data
        self.flags = flags
        self.length = len(data) + 6

    def raw_packet(self) -> bytes:
        """
        Generate raw packet from :class:`xc2.packets.XC2Packet` instance. It is used to send packet over the bus.
        """
        typedst = bytes([self.pktype | self.dst >> 8, self.dst & 0x0FF])
        flagssrc = bytes([self.flags | self.src >> 8, self.src & 0x0FF])
        length = self.length.to_bytes(1, byteorder="big")
        cmd = self.cmd.to_bytes(1, byteorder="big")
        packet_without_crc = bytes(typedst + flagssrc + length + cmd + self.data)
        crc = calc_xc2_crc(packet_without_crc)
        return packet_without_crc + crc.to_bytes(2, byteorder="big")

    @classmethod
    def parse_bytes(cls, buf) -> tuple["XC2Packet", bytes]:
        """Parse raw packet in bytes into packet class.

        :raises IncompletePacket: Raised when the packet is too short to be valid
        or the declared packet length is longer than the actual packet length
        :raises BadCrc: Raised when the CRC of the packet does not match the CRC in the packet
        :return: Tuple of packet class and trailing garbage (bytes)
        :rtype: tuple[XC2Packet, bytes]
        """
        # print(len(buf))
        if len(buf) < 8:  # minimum length of XC2 packet is 8 bytes
            raise IncompletePacket("Incomplete packet error. The packet is too short to be valid.")

        # now we can safely read packet length
        packet_length = buf[4]
        if len(buf) < packet_length + 2:  # two bytes extra for CRC
            raise IncompletePacket("Incomplete packet error. The declared packet length is longer than the actual packet length.")

        # check CRC
        crc_in_packet = ((buf[packet_length]) << 8) + (buf[packet_length + 1])
        if crc_in_packet != calc_xc2_crc(buf[0:packet_length]):
            raise BadCrc("Bad CRC error. The CRC of the packet does not match the CRC in the packet.")

        packet = cls(
            pkt_type=buf[0] & 0xF0,
            dst=((buf[0] & 0x0F) << 8) + buf[1],
            src=((buf[2] & 0x0F) << 8) + buf[3],
            cmd=buf[5],
            data=buf[6:packet_length] if packet_length > 6 else bytes([]),
            flags=buf[2] & 0xF0,
        )
        trailing_garbage = buf[packet_length + 2 : len(buf)]

        return packet, trailing_garbage


@dataclass(init=False)
class ModbusPacket(XC2Packet):
    """
    ModbusPacket class defining the structure of the packet. Child class of :class:`xc2.packets.XC2Packet`.
    :class:`xc2.packets.ModbusPacket` has the same structure as :class:`xc2.packets.XC2Packet` and
    is used just as a wrapper to follow the Modbus protocol. The only difference is the addition of
    the slave_id and fcn_code attributes.
        - slave_id - 8 bits - Slave address (0x00 - 0xFF), same as dst in :class:`xc2.packets.XC2Packet`
        - fcn_code - 8 bits - Function code (0x00 - 0xFF), usually an attribute of :class:`xc2.consts.XC2ModbusFceCode` enum
    """

    slave_id: int
    fcn_code: int

    def __init__(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags: XC2Flags = 0x0):
        """Constructor method.

        :param pkt_type: Value from :class:`xc2.consts.XC2PacketType` enum
        :type pkt_type: int | XC2PacketType
        :param dst: Destination address in 0xXXX format
        :type dst: hexadecimal
        :param src: Source address in 0xXXX format (0x001 for master)
        :type src: hexadecimal
        :param cmd: Command from :class:`xc2.consts.XC2Commands` enum
        :type cmd: int | XC2Commands
        :param data: Data to be packed into the packet, defaults to bytes([])
        :type data: bytes, optional
        :param flags: Flags from the :class:`xc2.consts.XC2Flags` enum (multicast, supress answer etc.), defaults to 0x0 (No flag)
        :type flags: hexadecimal, optional
        """
        super().__init__(pkt_type, dst, src, cmd, data, flags)
        self.slave_id = dst
        self.fcn_code = XC2ModbusFceCode.XC2_PACKET_FCN

    def raw_packet(self):
        """
        Generate raw packet from :class:`xc2.packets.ModbusPacket` instance. It is used to send packet over the bus.
        """
        slave_id_bytes = self.slave_id.to_bytes(1, byteorder="big")
        fcn_code_bytes = self.fcn_code.to_bytes(1, byteorder="big")
        pkt_without_crc = bytes(slave_id_bytes + fcn_code_bytes + super().raw_packet())
        crc = calc_modbus_crc(pkt_without_crc)
        return pkt_without_crc + crc

    @classmethod
    def parse_bytes(cls, buf) -> tuple["ModbusPacket", bytes]:
        """Parse raw packet in bytes into packet class.

        :raises IncompletePacket: Raised when the packet is too short to be valid
        or the declared packet length is longer than the actual packet length
        :raises BadCrc: Raised when the CRC of the packet does not match the CRC in the packet
        :return: Tuple of packet class and trailing garbage (bytes)
        :rtype: tuple[ModbusPacket, bytes]
        """

        if len(buf) < 12:  # minimum length of Modbus XC2 packet is 12 bytes
            raise IncompletePacket()

        packet_length = buf[6]
        if len(buf) < packet_length + 2:  # two bytes extra for CRC
            raise IncompletePacket()

        pkt_len = len(buf) - 2  # len of crc

        raw_xc2_pkt = buf[struct.calcsize("!BB") : pkt_len]
        trailing_garbage = buf[pkt_len:]

        check_crc = calc_modbus_crc(buf[:pkt_len])
        if check_crc != trailing_garbage:
            raise BadCrc()

        xc2_pkt = super().parse_bytes(raw_xc2_pkt)[0]

        pkt = cls(
            pkt_type=xc2_pkt.pktype,
            dst=xc2_pkt.dst,
            src=xc2_pkt.src,
            cmd=xc2_pkt.cmd,
            data=xc2_pkt.data,
            flags=xc2_pkt.flags,
        )
        return pkt, trailing_garbage


# @dataclass(init=False)
class XCTPacket:
    pktype: int
    dst: str
    src: int
    cmd: int
    data: str
    length: int  # = 6  #minimum packet length is 6 bytes

    def __init__(self, pkt_type, dst, cmd, data: str = "", fix_length: int = None, ack_str: str = ""):
        self.pktype = pkt_type
        self.dst = dst
        self.cmd = cmd
        self.data = data
        self.ack_str = ack_str
        if fix_length is not None:
            self.length = fix_length
        else:
            self.length = len(data)

    @classmethod
    def parse_bytes(cls, buf: bytes | str) -> tuple["XCTPacket", bytes]:
        ack_str = ""
        if isinstance(buf, bytes):
            ret = buf.decode("utf8")
        else:
            ret = buf
        if not ret.startswith("OK"):
            ret_pqt = XCTPacket(XCTPacketType.ANSWER, XC2Addr.MASTER, XCTCommands.ERROR, ret.strip())
            return ret_pqt, b""
        if ret.startswith("OK 200 "):
            ret = ret[7:].strip()
            ack_str = "OK 200"
        else:
            ret = ret[3:].strip()
            ack_str = "OK"
        ret_pqt = XCTPacket(XCTPacketType.ANSWER, XC2Addr.MASTER, XCTCommands.OK, ret, fix_length=len(buf), ack_str=ack_str)
        return ret_pqt, b""

    def raw_packet(self) -> bytes:
        """
        Generate raw packet from :class:`xc2.packets.XCTPacket` instance. It is used to send packet over the bus.
        """
        ret = b""
        if self.pktype == XCTPacketType.DEVICE:
            if self.cmd in [XCTCommands.GET, XCTCommands.SET]:
                ret = f"{self.cmd} {self.dst}.{self.data}\n"
            elif self.cmd == XCTCommands.REST:
                ret = f"{self.cmd} {self.data}\n"
            else:
                raise NotImplementedError("Cannot parse to raw_packet")
        elif self.pktype == XCTPacketType.SERVER:
            if self.cmd in [XCTCommands.GET, XCTCommands.SET]:
                ret = f"{self.cmd} {self.data}\n"
            elif self.cmd == XCTCommands.ECHO:
                ret = "ECHO\n"
            elif self.cmd == XCTCommands.PLAIN_CMD:
                if len(self.data) == 0:
                    raise ValueError("Cannot send empty command")
                ret = f"{self.data}"
                if not ret.endswith("\n"):
                    ret = ret + "\n"
            else:
                raise NotImplementedError("Cannot parse to raw_packet")

        return ret.encode("utf8")
