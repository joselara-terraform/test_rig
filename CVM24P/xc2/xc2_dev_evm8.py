import logging
import threading
from .consts import XC2Addr, DeviceType
from .bus import BusBase, TCPBus
from .xc2_device import XC2Device
from .consts import DeviceStatus
from .utils import bytes_to_int48
import asyncio
import copy


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


class XC2Evm8(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        alt_name: str = None,
        max_ttl: int = 5,
        dev_type: DeviceType = DeviceType.Evm8,
        data_socket_port: int = 17002,
        status: DeviceStatus = DeviceStatus.Expected,
    ):
        super().__init__(
            bus,
            addr,
            alt_name=alt_name,
            max_ttl=max_ttl,
            dev_type=dev_type,
            status=status,
        )
        self.evm_data_reader = None
        self.data_socket_port = data_socket_port
        self.running_data_socket = False
        self.receive_task = None
        self.evm_data_buffer = DataBuffer()
        self.waiting_for_header = True
        self.waiting_for_evm_data = False
        self.emv_data_total_packets = 0
        self.evm_data_packet_size = 0
        self.evm_data_channels = 0
        self.first_app_reg = 21

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        raise NotImplementedError("Restore registers is not implemented in EVM8")
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!ffff ffff fffff   BBBB"
        #                 0  4 5  8 9   13 14  17

    #         parser_str_1 = "!fffffffffffffBBBB"
    #         data = self.app_status_raw
    #         data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])
    #
    #         self.edac_value = data_1[0:4]
    #         self.adc_value = data_1[4:8]
    #         self.mon_V = data_1[8:13]
    #         self.output_status = data_1[13:17]

    def read_app_status(self):
        raise NotImplementedError("Restore registers is not implemented in EVM8")

    #         return {
    #             "edac_value": self.edac_value,
    #             "adc_value": self.adc_value,
    #             "mon_V": self.mon_V,
    #             "output_status": self.output_status,
    #         }

    def read_and_get_app_status(self):
        raise NotImplementedError("Restore registers is not implemented in EVM8")

    async def start_data_socket(self):
        if not isinstance(self.bus, TCPBus):
            raise NotImplementedError("cannot start data stream on non TCPbus")
        if self.is_running():
            try:
                self.data_socket_port = await self.read_and_get_reg_by_name("tcp_data_sender_server_port")
            except Exception as e:
                logging.error(f"Unable to get tcp_data_sender_server_port: {e}\n\tusing default 17002")

        coro = asyncio.open_connection(self.bus.server_addr[0], self.data_socket_port)
        try:
            self.evm_data_reader, _ = await asyncio.wait_for(coro, 1)
            self.running_data_socket = True
            self.receive_task = asyncio.create_task(self.receive_evm_data())
        except asyncio.TimeoutError:
            self.running_data_socket = False
            if self.receive_task is not None:
                self.receive_task.cancel()

    async def receive_evm_data(self):
        print(f"{self.alt_name}: RUNNING RECEIVE EVM DATA")
        try:
            self.waiting_for_header = True
            self.waiting_for_evm_data = False
            trailing_data = b""
            old_counter = 0
            PACKETS = 0
            while self.running_data_socket:
                coro = self.evm_data_reader.read(1024 - len(trailing_data))
                try:
                    data = await asyncio.wait_for(coro, 0.5)
                except asyncio.TimeoutError:
                    if self.waiting_for_evm_data:
                        self.evm_data_buffer.add_data({"cmd": "evm_data", "status": "TIMEOUT ERROR"})
                        data = b""
                    else:
                        data = await self.evm_data_reader.read(1024)
                if not data:
                    self.waiting_for_header = True
                    self.waiting_for_evm_data = False
                    trailing_data = b""
                    old_counter = 0
                    PACKETS = 0
                    continue
                if self.waiting_for_header:
                    self.waiting_for_header = False
                    self.waiting_for_evm_data = True
                    self.decode_evm_data_header(data)
                elif self.waiting_for_evm_data:
                    if len(trailing_data):
                        data = trailing_data + data
                        trailing_data = b""
                    mod = len(data) % 32
                    if mod:
                        trailing_data = data[len(data) - mod :]
                        data = data[:-mod]
                    PACKETS += int(len(data) / 32)
                    try:
                        old_counter = await self.decode_evm_data(data, old_counter)
                    except Exception:
                        logging.error(f"{self.alt_name}: ERROR while parsing EVM DATA")
                    if PACKETS == self.evm_data_packet_size:
                        self.waiting_for_header = True
                        self.waiting_for_evm_data = False
                        trailing_data = b""
                        old_counter = 0
                        PACKETS = 0
                        print(f"{self.alt_name}: PACKET_SIZE REACHED")
                        self.evm_data_buffer.add_data({"cmd": "evm_data", "status": "DONE"})

                await asyncio.sleep(0)

        except Exception as e:
            logging.error(e)
            self.evm_receive_stop()
            await self.start_data_socket()

    def evm_receive_stop(self):
        self.evm_data_buffer.clear_data()
        self.running_data_socket = False
        if self.receive_task is not None:
            self.receive_task.cancel()

    def decode_evm_data_header(self, header: bytes):
        header = header.decode().strip()
        # header_strings = ["TYPE", "DECMCU", "DECFPGA", "DATA_PACKET_SIZE", "PACKETS"]
        header = header.split(";")
        tmp = {}
        for attr in header:
            if ":" not in attr:
                continue
            attr = attr.split(":")
            name, value = attr[0], int(attr[1], 16)
            match name:
                case "DATA_PACKET_SIZE":
                    self.evm_data_packet_size = value
                case "PACKETS":
                    self.emv_data_total_packets = value
                case "CHANNELS":
                    self.evm_data_channels = value
            tmp[name] = value
        self.evm_data_buffer.add_data({"cmd": "evm_data", "status": "header1", "data": tmp})

    async def decode_evm_data(self, data, old_counter: int = 0):
        ind = 0
        old_ID = 7
        counter = 0
        gains = self.get_reg_by_name("evm_data_gain")
        timer1_IDs = []
        timer1_complete = False
        timer2_IDs = []
        timer2_complete = False
        if not gains:
            gains = len(self.get_reg_by_name("evm_data_avg")) * [1]
        offsets = self.get_reg_by_name("evm_data_offset")
        if not offsets:
            offsets = len(self.get_reg_by_name("evm_data_avg")) * [0]
        while True:
            try:
                measurements = data[ind : ind + 32]
                if not measurements:
                    raise IndexError
            except IndexError:
                break

            try:
                for i in range(0, 32, 4):
                    group = measurements[i : i + 4]
                    group = bytearray(group)
                    ID = group[0]
                    if not ID & 0b1:
                        self.evm_data_buffer.add_data({"cmd": "evm_data", "bytes": f"{group.hex()}", "status": "INVALID DATA BIT SET"})
                        continue
                    if ID & 0b10:
                        if not timer1_complete:
                            timer1_IDs.append(group[0] & 0xFC)
                            if len(timer1_IDs) == 8:
                                timer1_complete = bytes_to_int48(timer1_IDs)
                        elif not timer2_complete:
                            counter = 1
                            timer2_IDs.append(group[0] & 0xFC)
                            if len(timer2_IDs) == 8:
                                timer2_complete = bytes_to_int48(timer2_IDs, 1)
                                self.evm_data_buffer.priority_add({"cmd": "evm_data", "status": "time_stamp_diff", "data": timer1_complete - timer2_complete})
                                self.evm_data_buffer.priority_add({"cmd": "evm_data", "status": "time_stamp_1", "data": timer2_complete})
                                self.evm_data_buffer.priority_add({"cmd": "evm_data", "status": "time_stamp_0", "data": timer1_complete})

                        ID = int(i / 4) % 8
                        old_ID = copy.copy(ID)
                        old_counter = copy.copy(counter)

                    else:
                        counter = (ID & 0x0F) >> 2
                        ID = (ID & 0xF0) >> 5
                        if counter != old_counter:
                            if (counter > 0 and (counter - old_counter != 1)) or (counter == 0 and old_counter != 3):
                                self.evm_data_buffer.add_data({"cmd": "evm_data", "c": counter, "old_c": old_counter, "status": "INVALID_DATA COUNTER"})
                                logging.error(f"{self.alt_name}: WRONG EVM DATA COUNTER")
                                #     print(f"\nInvalid date in data[{ind},{ind+32}]")
                                continue

                        old_counter = copy.copy(counter)

                        if (ID > 0 and ID - old_ID != 1) or (ID == 0 and old_ID != 7):
                            self.evm_data_buffer.add_data({"cmd": "evm_data", "id": ID, "o_id": old_ID, "status": "INVALID_DATA IDs"})
                            #  print(f"\nInvalid date in data[{ind},{ind+32}]")
                            logging.error(f"{self.alt_name}: WRONG EVM DATA ID")
                            continue

                        old_ID = copy.copy(ID)

                    gain = gains[ID]
                    offset = offsets[ID]

                    val = int.from_bytes(group[1:], byteorder="little", signed=True) * gain + offset
                    self.evm_data_buffer.add_data({"cmd": "evm_data", "channel": ID, "counter": counter, "status": "value", "data": val})
                    await asyncio.sleep(0)
                ind += 32

            except Exception as e:
                raise e

        return old_counter
