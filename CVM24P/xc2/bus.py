import asyncio
import logging
import serial_asyncio
import struct
import time
import typing
from typing import Union

from .consts import (
    ProtocolEnum,
    TIMEOUT_RESPONSE,
    XC2Addr,
    XC2Commands,
    XCTCommands,
    XC2PacketType,
    XC2SysSubcommands,
    LogPktType,
    BusStatus,
)
from .xc2_except import (
    IncompletePacket,
    BadCrc,
    XC2TimeoutError,
    GeneralError,
    UnexpectedAnswerError,
)
from .xct_except import XCTError
from .protocol import XC2ProtocolBase, ModbusProtocolBase, XCTProtocolBase
from .packets import XC2Packet, ModbusPacket, XCTPacket
from .comm_logger import PySideLogger


class BusBase:
    """Base class for all buses (serial, TCP, etc.). Contains common methods and attributes."""

    def __init__(
        self,
        protocol_type: ProtocolEnum,
        bus_name: str = None,
        discovery_time: int = 0,
        log_bytes: bool = False,
        logger: PySideLogger = None,
        default_timeout: int = TIMEOUT_RESPONSE,
        status: BusStatus = BusStatus.Expected,
    ):
        """
        :param protocol_type: Protocol type of the bus in which the communication is done
        :type protocol_type: ProtocolEnum
        :param bus_name: Name of the bus, defaults to None. When left as None, it is generated depending
                         on the implementation of child class
        :type bus_name: str, optional
        :param discovery_time: Determines how long in seconds is the waiting time before communication starts, defaults to 0
        :type discovery_time: int, optional
        :param log_bytes: Enables or disables logging of actions on the bus, defaults to False
        :type log_bytes: bool, optional
        :param logger: :any:`comm_logger.PySideLogger` object for logging, defaults to None
        :type logger: PySideLogger | None, optional
        :param default_timeout: Default timeout for receiving packets, defaults to TIMEOUT_RESPONSE
        :type default_timeout: int, optional
        :param status: Status of the bus. Indicates what state the master considers the bus to be in.
                       For list of states, read :any:`BusStatus`, defaults to :any:`BusStatus.Expected`
        :type status: :any:`BusStatus`, optional
        """
        self.protocol_type = protocol_type
        if protocol_type == ProtocolEnum.Modbus:
            self.protocol = ModbusProtocolBase()
        elif protocol_type == ProtocolEnum.XCT:
            self.protocol = XCTProtocolBase()
        else:
            self.protocol = XC2ProtocolBase()
        self.status = status
        self.status_changed = False
        self.discovery_time = discovery_time
        self.bus_name = bus_name
        self.log_bytes = log_bytes
        self.logger = logger
        self.default_timeout = default_timeout
        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None
        self._buf: bytes = b""
        self.events_buffer: list[XC2Packet] = []
        self.max_reader_size = 1024

    def change_protocol(self, protocol_type: ProtocolEnum):
        """Changes protocol of the bus.

        :param protocol_type: Protocol type of the bus in which the communication is done
        :type protocol_type: :any:`ProtocolEnum`
        """
        match protocol_type:
            case ProtocolEnum.XC2:
                self.protocol = XC2ProtocolBase()
            case ProtocolEnum.Modbus:
                self.protocol = ModbusProtocolBase()
            case ProtocolEnum.XCT:
                self.protocol = XCTProtocolBase()
            case _:
                # TODO: custom exception
                pass

    def get_bus_long_name(self) -> str:
        """
        Returns long name of the bus. It is implementation specific for each child class.

        :return: Long name of the bus
        :rtype: str
        """
        raise NotImplementedError

    def enable_logging(self, enable: bool):
        """Enables or disables logging of actions on the bus.

        :param enable: True to enable logging, False to disable
        :type enable: bool
        """

        self.log_bytes = enable

    def is_logging(self) -> bool:
        """Returns if logging is enabled or disabled.

        :return: True if logging is enabled, False if disabled
        :rtype: bool
        """
        return self.log_bytes

    def log(self, pkt: XC2Packet, pkt_type: LogPktType, back_msg=False):
        """Logs packet to the logger if it is enabled.

        :param pkt: Packet to be logged
        :type pkt: XC2Packet
        :param pkt_type: Type of the packet. See :any:`LogPktType` for available types of packet.
        :type pkt_type: LogPktType
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        """
        if self.logger is not None:
            self.logger.log_pkt(pkt=pkt, log_type=pkt_type, background_msg=back_msg)

    async def send_raw_bytes(self, bytes_msg: bytes, timeout: int = 400):
        """Sends raw bytes to the bus. When the connection is reset during sending the packet, it tries to resend it up to 3 times.

        :param bytes_msg: Packet in raw bytes format to be sent to the bus
        :type bytes_msg: bytes
        :param timeout: Timeout for sending the raw packet in ms, defaults to 400
        :type timeout: int, optional
        :raises e: Raises :any:`ConnectionResetError` if the connection is reset during sending the packet
        """
        for i in range(3):
            try:
                self.writer.write(bytes_msg)
                await self.writer.drain()
                break
            except ConnectionResetError as e:
                if i == 2:
                    raise e
                await asyncio.sleep(timeout / 1000)
                await self.connect(timeout=timeout)

    async def send_pkt(self, pkt: XC2Packet):
        """Sends XC2 packet to the bus. The packet is converted to bytes first
        and then sent to the bus by :any:`BusBase.send_raw_bytes` method.

        :param pkt: Packet to be sent to the bus
        :type pkt: XC2Packet
        """
        raw_bytes = self.protocol.pkt_to_bytes(pkt)
        await self.send_raw_bytes(raw_bytes)

    async def receive_pkt(self, timeout=None) -> XC2Packet:
        """Receives XC2 packet from the bus. It reads bytes from the bus asynchronously
        and tries to parse them to XC2 packet. If the packet is not received in the given timeout,
        it raises :any:`XC2TimeoutError`.

        :param timeout: Timeout for receiving the packet in ms, defaults to bus defaults
        :type timeout: int, optional
        :raises XC2TimeoutError: Raises :any:`XC2TimeoutError` if the packet is not received in the given timeout
        :return: Received packet
        :rtype: XC2Packet
        """
        if timeout is None:
            timeout = self.default_timeout
        start_time = time.time_ns()
        big_packet = False
        while True:
            read_coro = self.reader.read(self.max_reader_size)
            try:
                new_bytes = await asyncio.wait_for(read_coro, timeout=timeout / 1000)
            except asyncio.TimeoutError:
                if not big_packet:
                    self._buf = b""  # clear incoming buffer
                    raise XC2TimeoutError(f"Didn't received response in {timeout} ms")
                new_bytes = b""
            if len(new_bytes) > 0:
                self._buf += new_bytes
            if len(new_bytes) == self.max_reader_size:
                big_packet = True
                continue
            if len(self._buf) >= self.protocol.pkt_min_len:
                try:
                    pkt, self._buf = self.protocol.parse_bytes(self._buf)
                    return pkt
                except IncompletePacket:
                    pass
                except XCTError:
                    raise XCTError
                except BadCrc:
                    self._buf = b""  # clear incoming buffer because we are probably lost
            # check for timeout
            if time.time_ns() - start_time > timeout * (1e6):
                self._buf = b""  # clear incoming buffer
                raise XC2TimeoutError(f"Didn't received response in {timeout} ms")

    async def read_event(self):
        """Reads event from the bus. If the :any:`BusBase.events_buffer` is not empty,
        it returns the first event from the buffer. Otherwise it reads bytes from the
        bus asynchronously and tries to parse them to XC2 packet. If the packet is not
        received in the given timeout (0.1 ms), it raises :any:`XC2TimeoutError`.

        :return: Received event
        :rtype: XC2Packet
        """
        if self.events_buffer:
            return self.events_buffer.pop(0)
        read_coro = self.reader.read(1024)
        try:
            self._buf = await asyncio.wait_for(read_coro, timeout=0.0001)
        except asyncio.TimeoutError:
            self._buf = b""  # clear incoming buffer
            return 0
        # print("I am here")
        if len(self._buf) >= self.protocol.pkt_min_len:  # 8 is nminimum XC2 packet length
            try:
                pkt, self._buf = self.protocol.parse_bytes(self._buf)
                return pkt
            except IncompletePacket:
                pass
            except BadCrc:
                self._buf = b""  # clear incoming buffer because we are probably lost

    def clear_buffers(self):
        """Clears incoming buffer."""
        self._buf = b""

    def close(self):
        """Sets the status of the bus to :any:`BusStatus.Disconnected` and closes the connection."""
        self.status = BusStatus.Disconnected
        self.status_changed = True
        if self.writer is not None:
            try:
                self.writer.close()
            except Exception as e:
                logging.error(f"Unable to close writer: {e}")
        self.writer = None
        self.reader = None

    async def request_response(self, req_pkt: XC2Packet, timeout=None) -> XC2Packet:
        """Sends XC2 packet to the bus and waits for response. If the response is not received in the given timeout,
        it raises :any:`XC2TimeoutError`. If the response is not the expected response, :any:`UnexpectedAnswerError` is raised.

        :param req_pkt: Packet to be sent to the bus
        :type req_pkt: XC2Packet
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :raises GeneralError: Raised when the destination address of the packet is broadcast address.
        :raises UnexpectedAnswerError: Raised when the received packet is not the expected response
                                       or when the received packet is not an event.
        :return: Received packet
        :rtype: XC2Packet
        """
        timeout = timeout if timeout else self.default_timeout
        if req_pkt.dst == XC2Addr.BROADCAST:
            raise GeneralError("Cannot send request-response to broadcast address")

        # TODO: read event instead of clearing buffers
        self.clear_buffers()  # we don't care about anything in buffer since we are expecting response
        await self.send_pkt(req_pkt)
        for attempt in range(10):  # 10 EVENTS in a row are unlikely
            recv_pkt = await self.receive_pkt(timeout)
            if isinstance(recv_pkt, XCTPacket):
                return recv_pkt
            if recv_pkt.cmd != req_pkt.cmd or recv_pkt.src != req_pkt.dst:
                if recv_pkt.pktype == XC2PacketType.EVENT:
                    self.events_buffer.append(recv_pkt)
                    continue
                if attempt > 0:
                    raise UnexpectedAnswerError(f"Wrong response received: {recv_pkt}")
                if recv_pkt.pktype == XC2PacketType.NAK:
                    print(f"NAK received on bus {self.bus_name}")
                    return recv_pkt
                else:
                    raise UnexpectedAnswerError(f"Wrong response received: {recv_pkt}")
            else:
                break
        return recv_pkt

    async def broadcast_pkt(self, pkt: XC2Packet, timeout=None) -> typing.List[XC2Packet]:
        """Broadcasts XC2 packet to the entire bus
        and waits for response. If the response is not received in the given
        timeout, :any:`XC2TimeoutError` is raised. Used by :any:`BusBase.broadcast` method.
        Internally similar to :any:`BusBase.request_response` method, but it optionally
        logs the packet to the logger.

        :param pkt: Packet to be sent to the bus
        :type pkt: XC2Packet
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :raises XC2TimeoutError: Raised when the response is not received in the given timeout
        :return: List of received packets
        :rtype: list[XC2Packet]
        """
        timeout = timeout if timeout else self.default_timeout
        pkt.dst = XC2Addr.BROADCAST
        self.clear_buffers()  # we don't care about anything in buffer since we are expecting response
        await self.send_pkt(pkt)
        if self.log_bytes:
            self.log(pkt=pkt, pkt_type=LogPktType.INPUT_PKT, back_msg=False)
            # print("Broadcast input")
        received_packets = []
        try:
            while True:
                pkt = await self.receive_pkt(timeout)
                received_packets.append(pkt)
                if self.log_bytes:
                    self.log(pkt=pkt, pkt_type=LogPktType.OUTPUT_PKT, back_msg=False)
                    # print("Broadcast output")
        except XC2TimeoutError:
            pass
        # FIXME: takhle se to nepise (podle me)

        if received_packets:
            return received_packets
        else:
            raise XC2TimeoutError(f"Didn't receive any response on broadcast in {timeout} ms")

    async def unicast_pkt(self, pkt: XC2Packet, req_response=True, timeout=None, back_msg=False):
        """Sends XC2 packet to the bus and waits for response.
        Uses :any:`BusBase.send_pkt_with_response` and :any:`BusBase.send_pkt_no_response` methods
        to send packets.

        :param pkt: Packet to be sent to the bus
        :type pkt: XC2Packet
        :param req_response: Whether to wait for response, defaults to True
        :type req_response: bool, optional
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        :return: If :any:`req_response` is True, returns received data in form of bytes. Otherwise returns True.
        :rtype: bytes | bool
        """
        if req_response:
            return await self.send_pkt_with_response(pkt=pkt, timeout=timeout, back_msg=back_msg)
        else:
            return await self.send_pkt_no_response(pkt=pkt, back_msg=back_msg)

    async def broadcast(
        self,
        pkt_type: XC2PacketType,
        src: Union[XC2Addr, int],
        cmd: XC2Commands,
        data=b"",
        flags=0x00,
        timeout=None,
    ):
        """Generates valid XC2 packet and broadcasts it to the entire bus.
        Returns list of received packets.

        :param pkt_type: Valid :any:`XC2PacketType` enum value
        :type pkt_type: XC2PacketType
        :param src: Source address in 0xXXX format (0x001 for master). Typically set to 0x001.
        :type src: int | XC2Addr
        :param cmd: Valid :any:`XC2Commands` enum value
        :type cmd: XC2Commands
        :param data: Data to be sent in the packet, defaults to b""
        :type data: bytes, optional
        :param flags: Flags to be sent in the packet, defaults to 0x00
        :type flags: hexadecimal | :any:`XC2Flags`, optional
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :return: List of received packets
        :rtype: list[XC2Packet]
        """
        req_pkt = self.protocol.create_pkt(
            pkt_type=pkt_type,
            dst=XC2Addr.BROADCAST,
            src=src,
            cmd=cmd,
            data=data,
            flags=flags,
        )
        return await self.broadcast_pkt(
            pkt=req_pkt,
            timeout=timeout,
        )

    async def unicast(
        self,
        pkt_type: XC2PacketType,
        dst: Union[XC2Addr, int],
        src: Union[XC2Addr, int],
        cmd: XC2Commands,
        data=b"",
        flags=0x00,
        timeout=None,
        req_response=True,
        back_msg=False,
    ):
        """Generates valid XC2 packet and sends it to device specified
        by :any:`dst` parameter. Returns received data. If :any:`req_response` is True,
        it waits for response. Otherwise it just sends the packet and returns True.

        :param pkt_type: Valid :any:`XC2PacketType` enum value
        :type pkt_type: XC2PacketType
        :param dst: Destination address in 0xXXX format.
        :type dst: int | XC2Addr
        :param src: Source address in 0xXXX format (0x001 for master). Typically set to 0x001.
        :type src: int | XC2Addr
        :param cmd: Valid :any:`XC2Commands` enum value
        :type cmd: XC2Commands
        :param data: Data to be sent in the packet, defaults to b""
        :type data: bytes, optional
        :param flags: Flags to be sent in the packet, defaults to 0x00
        :type flags: hexadecimal | :any:`XC2Flags`, optional
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :param req_response: Whether to wait for response, defaults to True
        :type req_response: bool, optional
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        :return: If :any:`req_response` is True, returns received data in form of bytes. Otherwise returns True.
        :rtype: bytes | bool
        """
        req_pkt = self.protocol.create_pkt(pkt_type=pkt_type, dst=dst, src=src, cmd=cmd, data=data, flags=flags)
        return await self.unicast_pkt(pkt=req_pkt, req_response=req_response, timeout=timeout, back_msg=back_msg)

    async def send_pkt_no_response(self, pkt: XC2Packet, back_msg=False):
        """Sends XC2 packet to the bus without waiting for response.

        :param pkt: Packet to be sent to the bus
        :type pkt: XC2Packet
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        :return: True
        :rtype: bool
        """
        self.clear_buffers()  # we don't care about anything in buffer
        await self.send_pkt(pkt)
        if self.log_bytes:
            self.log(pkt=pkt, pkt_type=LogPktType.INPUT_PKT, back_msg=back_msg)
        return True
        # TODO: return what?

    async def send_pkt_with_response(
        self,
        pkt: XC2Packet,
        timeout=None,
        back_msg=False,
        return_pkt=False,
    ) -> XC2Packet | XCTPacket | bytes:
        """Sends XC2 packet to the bus and waits for response.

        :param pkt: Packet to be sent to the bus
        :type pkt: XC2Packet
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        :param return_pkt: Returns whole packet if True, otherwise returns only data, defaults to False
        :type return_pkt: bool, optional
        :return: If :any:`return_pkt` is True, returns received packet. Otherwise returns received data in form of bytes.
        :rtype: XC2Packet | bytes
        """
        if self.log_bytes:
            self.log(pkt=pkt, pkt_type=LogPktType.INPUT_PKT, back_msg=back_msg)
        rcvt_pkt = await self.request_response(pkt, timeout)
        if self.log_bytes:
            self.log(pkt=rcvt_pkt, pkt_type=LogPktType.OUTPUT_PKT, back_msg=back_msg)
        if return_pkt:
            return rcvt_pkt
        return rcvt_pkt.data

    async def command(
        self,
        my_addr: Union[XC2Addr, int],
        device_addr: Union[XC2Addr, int, str],
        command: Union[XC2Commands | XCTCommands],
        data: bytes | str = b"",
        timeout=None,
        req_response=True,
        back_msg=False,
    ) -> bool | bytes:
        """Sends XC2 packet with command to the bus and waits for response.
        If :any:`req_response` is True, it waits for response. Otherwise it
        just sends the packet and returns True.

        :param my_addr: Source address in 0xXXX format (0x001 for master). Typically set to 0x001.
        :type my_addr: Union[XC2Addr, int]
        :param device_addr: Destination address in 0xXXX format.
        :type device_addr: Union[XC2Addr, int, str] str for XCT
        :param command: Valid :any:`XC2Commands` enum value
        :type command: XC2Commands
        :param data: Data to be sent in the packet, defaults to b""
        :type data: bytes, optional
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :param req_response: Whether to wait for response, defaults to True
        :type req_response: bool, optional
        :param back_msg: Whether to print 'BACK_' before the potential flags in the packet log, defaults to False
        :type back_msg: bool, optional
        :return: If :any:`req_response` is True, returns received data in form of bytes. Otherwise returns True.
        :rtype: bytes | bool
        """
        req_pkt: Union[XC2Packet, ModbusPacket, XCTPacket]
        req_pkt = self.protocol.create_pkt(
            pkt_type=XC2PacketType.COMMAND,
            dst=device_addr,
            src=my_addr,
            cmd=command,
            data=data,
        )
        ret = await self.unicast_pkt(pkt=req_pkt, req_response=req_response, timeout=timeout, back_msg=back_msg)
        return ret

    async def sys_command(
        self,
        my_addr,
        device_addr,
        subcommand: XC2SysSubcommands,
        val=None,
        val_parse_str="",
        timeout=None,
        req_response=True,
    ) -> Union[XC2Packet, bytes]:
        """Sends XC2 packet with :any:`XC2Commands.CMD_SYS` command and system subcommand to a
        specific device on the bus and waits for response. Optionally it sends value in the packet.
        If :any:`val` is not None, it is packed to bytes according to :any:`val_parse_str` and
        sent in the packet. If :any:`val` is None, only the subcommand is sent in the packet.

        :param my_addr: Source address in 0xXXX format (0x001 for master). Typically set to 0x001.
        :type my_addr: XC2Addr | int
        :param device_addr: Destination address in 0xXXX format.
        :type device_addr: Union[XC2Addr, int]
        :param subcommand: Valid :any:`XC2SysSubcommands` enum value
        :type subcommand: XC2SysSubcommands
        :param val: Value to be sent in the packet, defaults to None
        :type val: Any, optional
        :param val_parse_str: Format string for packing :any:`val` to bytes, defaults to ""
        :type val_parse_str: str, optional
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :param req_response: Whether to wait for response, defaults to True
        :type req_response: bool, optional
        :return: Returns received data in form of bytes.
        :rtype: bytes
        """
        timeout = timeout if timeout else self.default_timeout
        subcommand_int = int(subcommand)
        # data = bytes([subcommand])
        if val is not None and val_parse_str != "":
            data = struct.pack(f"!B{val_parse_str}", subcommand_int, val)
        else:
            data = struct.pack("!B", subcommand_int)
        return await self.command(my_addr, device_addr, XC2Commands.CMD_SYS, data, timeout, req_response=req_response)

    async def reg_command(self, my_addr, device_addr, command: XC2Commands, data, timeout=None):
        """Sends XC2 packet with command specified in :any:`command` parameter
        with data specified in :any:`data` to a specific device on the bus.
        Returns received data. This method is used just as a wrapper for
        :any:`BusBase.command` method without additional functionality.

        :param my_addr: Source address in 0xXXX format (0x001 for master). Typically set to 0x001.
        :type my_addr: Union[XC2Addr, int]
        :param device_addr: Destination address in 0xXXX format.
        :type device_addr: Union[XC2Addr, int]
        :param command: Valid :any:`XC2Commands` enum value
        :type command: XC2Commands
        :param data: Data to be sent in the packet
        :type data: bytes
        :param timeout: Timeout for receiving the packet in ms. If left as None, the default timeout
                        set by :any:`BusBase.default_timeout` is used, defaults to None
        :type timeout: int | None, optional
        :return: Returns received data in form of bytes.
        :rtype: bytes
        """

        return await self.command(my_addr, device_addr, command, data, timeout)

    async def connect(self):
        """Connects to the bus. Implemented in child classes.

        :raises NotImplementedError: Raises :any:`NotImplementedError` if the method is not implemented in child class.
        """
        raise NotImplementedError("There is not way how to connect generic BusBase")


class SerialBus(BusBase):
    """Class for serial bus. Inherits from :any:`BusBase` class. it is used
    for communication with devices connected via serial line.
    """

    def __init__(
        self,
        bus_sn,
        baud_rate,
        protocol_type: ProtocolEnum,
        discovery_time: int = 0,
        port: str = None,
        bus_name: str = None,
        log_bytes=False,
        logger=None,
        default_timeout: int = TIMEOUT_RESPONSE,
    ):
        """
        :param bus_sn: Bus serial number
        :type bus_sn: str
        :param baud_rate: Baud rate of the serial line
        :type baud_rate: int
        :param protocol_type: Protocol type of the bus in which the communication is done
        :type protocol_type: ProtocolEnum
        :param discovery_time: Determines how long in seconds is the waiting time before communication starts, defaults to 0
        :type discovery_time: int, optional
        :param port: COM port used for the communicaiton, defaults to None
        :type port: str, optional
        :param bus_name: Name of the bus, defaults to None. When left as None, it is generated depending
                            on the implementation of child class
        :type bus_name: str, optional
        :param log_bytes: Enables or disables logging of actions on the bus, defaults to False
        :type log_bytes: bool, optional
        :param logger: :any:`comm_logger.PySideLogger` object for logging, defaults to None
        :type logger: PySideLogger | None, optional
        """
        super().__init__(protocol_type=protocol_type, discovery_time=discovery_time, log_bytes=log_bytes, logger=logger, default_timeout=default_timeout)
        self.bus_sn = bus_sn
        self.port = port  # TODO: maybe replace with USB identi PW...
        self.baud_rate = baud_rate
        if bus_name is None:
            self.bus_name = self.get_bus_long_name()
        else:
            self.bus_name = bus_name
        self.serial_line = None
        time.sleep(1)  # wait for serial line
        self._buf: bytes = b""

    async def connect(self):
        """Connects to the bus.

        :raises ConnectionError: Raised when the port is not defined
        """
        if self.port is None:
            raise ConnectionError("No port defined")
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=self.port, baudrate=self.baud_rate)

    def get_bus_long_name(self) -> str:
        """Returns long name of the bus. In case of this class, it is the port name.

        :return: Long name of the bus
        :rtype: str
        """
        return f"{self.bus_sn}"


class TCPBus(BusBase):
    """Class for TCP bus. Inherits from :any:`BusBase` class."""

    def __init__(
        self,
        ip_addr: str,
        port: int,
        protocol_type: ProtocolEnum,
        discovery_time: int = 0,
        bus_name: str = None,
        log_bytes=False,
        logger=None,
        is_brdige: bool = False,
        default_timeout: int = TIMEOUT_RESPONSE,
    ):
        """
        :param ip_addr: IP address of the device
        :type ip_addr: str
        :param port: Port used for the communication
        :type port: int
        :param protocol_type: Protocol type of the bus in which the communication is done
        :type protocol_type: ProtocolEnum
        :param discovery_time: Determines how long in seconds is the waiting time before communication starts, defaults to 0
        :type discovery_time: int, optional
        :param bus_name: Name of the bus, defaults to None. When left as None, it is generated depending
                            on the implementation of child class
        :type bus_name: str, optional
        :param log_bytes: Enables or disables logging of actions on the bus, defaults to False
        :type log_bytes: bool, optional
        :param logger: :any:`comm_logger.PySideLogger` object for logging, defaults to None
        :type logger: PySideLogger | None, optional
        :param is_brdige: Whether the device is a bridge to another bus/device, defaults to False
        :type is_brdige: bool, optional
        """
        super().__init__(protocol_type, log_bytes=log_bytes, logger=logger, discovery_time=discovery_time, default_timeout=default_timeout)
        self.server_addr: tuple[str, int] = (ip_addr, port)
        if bus_name is None:
            self.bus_name = self.get_bus_long_name()
        else:
            self.bus_name = bus_name
        self.is_bridge = is_brdige
        self.log_bytes: bool = log_bytes
        self._buf: bytes = b""

    def get_bus_long_name(self) -> str:
        """Returns long name of the bus. In case of this class, it is the IP address and port
        in format <IP>:<PORT>.

        :return: _description_
        :rtype: str
        """
        ip_addr, port = self.server_addr
        string = f"{ip_addr}:{port}"
        return string

    async def connect(self, timeout: int = 3000):
        """Connects to the bus. If the connection is not established in the given timeout,
        it raises :any:`XC2TimeoutError`.

        :param timeout: Timeout for connecting to the bus in ms, defaults to 3000
        :type timeout: int, optional
        :raises XC2TimeoutError: Raised when the connection is not established in the given timeout
        """
        coro = asyncio.open_connection(self.server_addr[0], self.server_addr[1])
        try:
            self.reader, self.writer = await asyncio.wait_for(coro, timeout=timeout / 1000)
        except asyncio.TimeoutError:
            self.status = BusStatus.Disconnected
            self.status_changed = True
            raise XC2TimeoutError(f"Bus: {self.bus_name} not available")
