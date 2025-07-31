import struct

from .consts import XC2Addr, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Rel(XC2Device):
    def __init__(self, bus: BusBase, addr=XC2Addr.DEFAULT, alt_name: str = None, max_ttl: int = 5):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Rel)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        # registr                data type in C      index in data1 app status
        self.out_ctrl = 0  # U8                 0
        self.mon_Tcpu = 0.0  # float              1
        self.mon_V = []  # float [3]          2:5
        self.out_status = []  # U8 [6]             5:11

    def read_app_status(self):
        return {
            "out_ctrl": self.out_ctrl,
            "mon_Tcpu": self.mon_Tcpu,
            "mon_V": self.mon_V,
            "out_status": self.out_status,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        self.parse_app_status_data()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!B f fff  BBBBBB"
        #                 0 1 2 4  5    10
        parser_str_1 = "!BffffBBBBBB"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])

        self.out_ctrl = data_1[0]
        self.mon_Tcpu = data_1[1]
        self.mon_V = data_1[2:5]
        self.out_status = data_1[5:11]

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in REL")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in REL")
