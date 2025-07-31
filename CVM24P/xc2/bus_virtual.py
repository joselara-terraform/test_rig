from random import randint

from .bus import BusBase
from .consts import ProtocolEnum, BusStatus
from .packets import XC2Packet


class VirtualBus(BusBase):
    """Virtual bus class for testing purposes."""

    def __init__(
        self,
        id: str,
        protocol_type: ProtocolEnum,
        discovery_time: int = 0,
        bus_name: str = None,
        log_bytes=False,
        logger=None,
    ):
        """Constructor for virtual bus class.

        :param id: ID of the bus
        :type id: str
        :param protocol_type: Protocol type of the bus in which the communication is done
        :type protocol_type: ProtocolEnum
        :param discovery_time: TODO: Zjistit o co jde, defaults to 0
        :type discovery_time: int, optional
        :param bus_name: Name of the bus, defaults to None. When left as None, it is generated
                         automatically in format "VirtualBus{random_number}"
        :type bus_name: str, optional
        :param log_bytes: Enables or disables logging of actions on the bus, defaults to False
        :type log_bytes: bool, optional
        :param logger: :any:`PySideLogger` object for logging, defaults to None
        :type logger: :any:`PySideLogger` | None, optional
        """
        super().__init__(
            protocol_type=protocol_type,
            discovery_time=discovery_time,
            log_bytes=log_bytes,
            logger=logger,
        )
        if bus_name is None:
            self.bus_name = self.get_bus_long_name()
        else:
            self.bus_name = bus_name
        self.id = id
        self.parent_buses: list = []

    async def connect(self):
        """Simulates the connection to the bus. Sets the status to `BusStatus.Available`."""
        self.status = BusStatus.Available

    def get_bus_long_name(self) -> str:
        """Generates the name of the bus."""
        return f"VirtualBus{randint(0, 1000)}"

    async def send_raw_bytes(self, bytes_msg: bytes):
        """Sends raw bytes to the bus. Not implemented.

        :param bytes_msg: Bytes to be sent
        :type bytes_msg: bytes
        """
        pass

    async def send_pkt(self, pkt: XC2Packet):
        """Sends the packet to the bus. Not implemented.

        :param pkt: Packet to be sent
        :type pkt: XC2Packet
        """
        pass

    async def receive_pkt(self, timeout=1000) -> XC2Packet:
        """Receives the packet from the bus. Not implemented.

        :param timeout: Packet receiving timeout in ms, defaults to 1000
        :type timeout: int, optional
        :return: Received packet
        :rtype: XC2Packet
        """
        pass

    async def read_event(self):
        """Reads the event from the bus. Not implemented."""
        pass

    def clear_buffers(self):
        """Clears the buffers of the bus. Not implemented."""
        pass

    def close(self):
        """Closes the bus. Sets the status to `BusStatus.Disconnected`."""
        self.status = BusStatus.Disconnected
