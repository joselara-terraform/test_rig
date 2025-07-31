import struct
import threading

from .consts import XC2Addr, DeviceType, XC2PacketType, XC2Commands
from .bus import BusBase

from .xc2_device import XC2Device


class DataBuffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.buffer = []

    def add_data(self, data):
        with self.lock:
            self.buffer.append(data)

    def priority_add(self, data):
        with self.lock:
            self.buffer.insert(0, data)

    def get_data(self):
        with self.lock:
            return self.buffer.pop(0) if self.buffer else None

    def clear_data(self):
        with self.lock:
            self.buffer.clear()

    def has_data(self):
        with self.lock:
            return bool(len(self.buffer))

    def get_len(self):
        with self.lock:
            return len(self.buffer)


class XC2Mis(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        alt_name: str = None,
        max_ttl: int = 5,
    ):
        self._reading = False
        self._read_data_buffer = DataBuffer()
        self._sample_rate = 0
        self._next_read_data_index = 0
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Mis)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        # registr                data type in C      index in data1 app status
        self.edac_value = []  # float [4]          0:4
        self.adc_value = []  # float [4]          4:8
        self.mon_V = []  # float [5]          8:13
        self.output_status = []  # U8 [4]             13:17

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!ffff ffff fffff   BBBB"
        #                 0  4 5  8 9   13 14  17
        parser_str_1 = "!fffffffffffffBBBB"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])

        self.edac_value = data_1[0:4]
        self.adc_value = data_1[4:8]
        self.mon_V = data_1[8:13]
        self.output_status = data_1[13:17]

    async def dac_offset(self, off_v: float = 0.0, off_i: float = 0.0):
        # Convert float values to bytes
        off_v_bytes = struct.pack(">f", off_v)
        off_i_bytes = struct.pack(">f", off_i)

        # Command header
        header = b"\x03\x00"

        # Concatenate all parts
        command_bytes = header + off_v_bytes + off_i_bytes
        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_C2,
            command_bytes,
        )
        await self.bus.send_pkt_with_response(packet_to_send)
        return True

    async def gen_start(self, amp: int | float, freq: int | float, reset_phase=False, phase: float = 0.0):
        # Convert float values to hex
        amp_bytes = struct.pack(">f", float(amp))
        freq_bytes = struct.pack(">f", float(freq))
        phase_bytes = struct.pack(">f", phase) if reset_phase else b""

        header = b"\x01\x00"
        command_bytes = header + amp_bytes + freq_bytes + phase_bytes
        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_C2,
            command_bytes,
        )
        await self.bus.send_pkt_with_response(packet_to_send)
        return True

    async def gen_stop(self):
        data = b"\x01\x03"
        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_C2,
            data,
        )
        await self.bus.send_pkt_with_response(packet_to_send)
        return True

    @staticmethod
    def hex_to_float(hex_str: bytes):
        return struct.unpack(">f", bytes.fromhex(hex_str.hex()))[0]

    async def acq_start_osci_by_periods(
        self,
        periods: int = 10,
        samples: int = 1024,
        range_a=1,
        range_b=1,
        gain_a=1.0,
        gain_b=1.0,
    ):
        # Convert values to bytes
        periods_bytes = struct.pack(">H", periods)
        samples_bytes = struct.pack(">H", samples)
        range_a_bytes = struct.pack(">B", range_a)
        range_b_bytes = struct.pack(">B", range_b)
        gain_a_bytes = struct.pack(">f", gain_a)
        gain_b_bytes = struct.pack(">f", gain_b)

        # Command header
        header = b"\x02\x02"

        # Concatenate all parts
        command_bytes = header + samples_bytes + periods_bytes + range_a_bytes + range_b_bytes + gain_a_bytes + gain_b_bytes
        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_C2,
            command_bytes,
        )
        ret = await self.bus.send_pkt_with_response(packet_to_send)
        self._reading = True
        self._sample_rate = self.hex_to_float(ret)
        return self._sample_rate

    async def acq_start_osci_by_rate(self, samplerate: float, samples=1024, range_a=1, range_b=1, gain_a=1.0, gain_b=1.0):
        # Convert values to bytes
        samples_bytes = struct.pack(">H", samples)
        samplerate_bytes = struct.pack(">f", samplerate)
        range_a_bytes = struct.pack(">B", range_a)
        range_b_bytes = struct.pack(">B", range_b)
        gain_a_bytes = struct.pack(">f", gain_a)
        gain_b_bytes = struct.pack(">f", gain_b)

        # Command header
        header = b"\x02\x03"

        # Concatenate all parts
        command_bytes = header + samples_bytes + samplerate_bytes + range_a_bytes + range_b_bytes + gain_a_bytes + gain_b_bytes

        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_C2,
            command_bytes,
        )
        ret = await self.bus.send_pkt_with_response(packet_to_send)
        self._reading = True
        self._sample_rate = self.hex_to_float(ret)
        return self._sample_rate

    def _parse_buffer_data(self, data: bytes):
        # Unpack the values
        running = struct.unpack(">B", data[0:1])[0]
        try:
            counter_data = data[1:5]
            if counter_data == b"":
                raise KeyError
            record_counter = struct.unpack(">I", counter_data)[0]
        except KeyError:
            if not running:
                self._reading = False
                self._next_read_data_index = 0
                return
        record_size = struct.unpack(">B", data[5:6])[0]
        next_index_offset = 0
        if len(data[6:]) > 0:
            data = data[6:]
            for i in range(0, len(data), record_size):  # Iterate over the remaining bytes, 8 bytes at a time
                if i + record_size <= len(data):  # Check if there are enough bytes left for a full record
                    record = struct.unpack(">ff", data[i : i + record_size])  # Unpack the next 8 bytes as two floats
                    self._read_data_buffer.add_data(record)
                    next_index_offset += 1
        self._next_read_data_index += next_index_offset

    async def read_buffer_cmd(self, tag=1, mask=3):
        # Convert values to bytes
        tag_bytes = struct.pack(">B", tag)
        mask_bytes = struct.pack(">B", mask)
        buf_index_bytes = struct.pack(">I", self._next_read_data_index)

        # Concatenate all parts
        command_bytes = tag_bytes + mask_bytes + buf_index_bytes
        packet_to_send = self.bus.protocol.create_pkt(
            XC2PacketType.COMMAND,
            self.addr,
            XC2Addr.MASTER,
            XC2Commands.CMD_MIS_BUFF,
            command_bytes,
        )
        ret = await self.bus.send_pkt_with_response(packet_to_send)
        self._parse_buffer_data(ret)

    def read_buffer_done(self):
        return (not self._reading) and (not self._read_data_buffer.has_data())

    def get_reading(self) -> bool:
        return self._reading

    async def read_buffer(self) -> dict:
        if self._read_data_buffer.has_data():
            data = []
            while self._read_data_buffer.has_data():
                dat = self._read_data_buffer.get_data()
                data.append(dat)
            return {"status": "data", "sample_rate": self._sample_rate, "data": data}
        return {"status": "empty_buffer"}

    def clear_read_buffer(self):
        self._next_read_data_index = 0
        self._reading = False
        self._read_data_buffer.clear_data()
