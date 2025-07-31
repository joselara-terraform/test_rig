from .consts import XC2PacketType, XC2Commands, XC2Flags
from .packets import XC2Packet, ModbusPacket, XCTPacket


class ProtocolBase:
    def __init__(self):
        pass


class XC2ProtocolBase(ProtocolBase):
    """XC2 Protocol Base Class.
    This class is used to create and parse XC2 packets. It mainly operates with :class:`xc2.packets.XC2Packet` class,
    which does all the work with packet creating and parsing."""

    def __init__(self):
        """Constructor method"""
        super().__init__()
        self.pkt_min_len = 8
        self.protocol_name = "XC2"

    def create_pkt(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags=0x0) -> XC2Packet:
        """Create XC2 packet with given parameters.

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
        :return: XC2Packet instance
        :rtype: XC2Packet
        """
        pkt = XC2Packet(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data, flags=flags)
        return pkt

    def raw_bytes(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags: XC2Flags = 0x0) -> bytes:
        """Create packet and convert it to bytes.

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
        :return: Raw bytes of the packet
        :rtype: bytes
        """
        pkt = XC2Packet(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data, flags=flags)
        return pkt.raw_packet()

    def pkt_to_bytes(self, pkt: XC2Packet) -> bytes:
        """Convert XC2Packet instance to bytes.

        :param pkt: XC2Packet instance
        :type pkt: XC2Packet
        :return: Raw bytes of the packet
        :rtype: bytes
        """
        # TODO: instance type control
        return pkt.raw_packet()

    def parse_bytes(self, buf: bytes) -> tuple[XC2Packet, bytes]:
        """Parse raw bytes into packet class.

        :param buf: Raw bytes of the packet
        :type buf: bytes
        :return: XC2Packet instance and trailing garbage in tuple
        :rtype: tuple[XC2Packet, bytes]
        """
        return XC2Packet.parse_bytes(buf)


class ModbusProtocolBase(ProtocolBase):
    """Modbus Protocol Base Class.
    This class is used to create and parse Modbus packets. It mainly operates with :class:`xc2.packets.ModbusPacket` class,
    which does all the work with packet creating and parsing. Pay attention to the fact that the addresses in Modbus protocol
    are in 0xXX format, while in XC2 protocol they are in 0xXXX format. This is because Modbus protocol standard uses only
    0x01 - 0xFF addresses with 0x00 being reserved for broadcast.

    :param ProtocolBase: Base class for all protocols
    :type ProtocolBase: ProtocolBase
    """

    def __init__(self):
        """Constructor method"""
        super().__init__()
        self.pkt_min_len = 12
        self.protocol_name = "MOD"

    def create_pkt(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags: XC2Flags = 0x0) -> ModbusPacket:
        """Create Modbus packet with given parameters.

        :param pkt_type: Value from :class:`xc2.consts.XC2PacketType` enum
        :type pkt_type: int | XC2PacketType
        :param dst: Destination address in 0xXX format
        :type dst: hexadecimal
        :param src: Source address in 0xXX format (0x01 for master)
        :type src: hexadecimal
        :param cmd: Command from :class:`xc2.consts.XC2Commands` enum
        :type cmd: int | XC2Commands
        :param data: Data to be packed into the packet, defaults to bytes([])
        :type data: bytes, optional
        :param flags: Flags from the :class:`xc2.consts.XC2Flags` enum (multicast, supress answer etc.), defaults to 0x0 (No flag)
        :type flags: hexadecimal, optional
        :return: ModbusPacket instance
        :rtype: ModbusPacket
        """
        pkt = ModbusPacket(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data, flags=flags)
        return pkt

    def raw_bytes(self, pkt_type: XC2PacketType, dst: int, src: int, cmd: XC2Commands, data=bytes([]), flags: XC2Flags = 0x0) -> bytes:
        """Create packet and convert it to bytes.

        :param pkt_type: Value from :class:`xc2.consts.XC2PacketType` enum
        :type pkt_type: int | XC2PacketType
        :param dst: Destination address in 0xXX format
        :type dst: hexadecimal
        :param src: Source address in 0xXX format (0x01 for master)
        :type src: hexadecimal
        :param cmd: Command from :class:`xc2.consts.XC2Commands` enum
        :type cmd: int | XC2Commands
        :param data: Data to be packed into the packet, defaults to bytes([])
        :type data: bytes, optional
        :param flags: Flags from the :class:`xc2.consts.XC2Flags` enum (multicast, supress answer etc.), defaults to 0x0 (No flag)
        :type flags: hexadecimal, optional
        :return: Raw bytes of the packet
        :rtype: bytes
        """

        pkt = ModbusPacket(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data, flags=flags)
        return pkt.raw_packet()

    def pkt_to_bytes(self, pkt: ModbusPacket) -> bytes:
        """Convert ModbusPacket instance to bytes.

        :param pkt: ModbusPacket instance
        :type pkt: ModbusPacket
        :return: Raw bytes of the packet
        :rtype: bytes
        """
        # TODO: instance type control
        return pkt.raw_packet()

    def parse_bytes(self, buf: bytes) -> tuple[ModbusPacket, bytes]:
        """Parse raw bytes into packet class.

        :param buf: Raw bytes of the packet
        :type buf: bytes
        :return: ModbusPacket instance and trailing garbage in tuple
        :rtype: tuple[ModbusPacket, bytes]
        """

        return ModbusPacket.parse_bytes(buf)


class XCTProtocolBase(ProtocolBase):
    def __init__(self):
        super().__init__()
        self.pkt_min_len = 1
        self.protocol_name = "XCT"

    @staticmethod
    def create_pkt(pkt_type, dst, src, cmd, data=bytes([])):
        pkt = XCTPacket(pkt_type=pkt_type, dst=dst, cmd=cmd, data=data)
        return pkt

    @staticmethod
    def raw_bytes(pkt_type, dst, src, cmd, data=bytes([]), flags=0x0):
        """
        Create pkt and convert to bytes
        """
        pkt = XCTPacket(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data)
        return pkt.raw_packet()

    def pkt_to_bytes(self, pkt: XCTPacket):
        # TODO: instance type control
        return pkt.raw_packet()

    def parse_bytes(self, buf):
        """
        Parse raw bytes into packet class
        """
        return XCTPacket.parse_bytes(buf)
