import struct

from .consts import XC2Addr, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Aio(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        alt_name: str = None,
        max_ttl: int = 5,
    ):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Aio)
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

    def read_app_status(self):
        return {
            "edac_value": self.edac_value,
            "adc_value": self.adc_value,
            "mon_V": self.mon_V,
            "output_status": self.output_status,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        return self.read_app_status()

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in AIO")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in AIO")
