import struct

from .consts import XC2Addr, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Pmm(XC2Device):
    def __init__(self, bus: BusBase, addr=XC2Addr.DEFAULT, alt_name: str = None, max_ttl: int = 5):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Pmm)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        # registr                data type in C      index in data1 app status
        self.mon_Tcpu = 0.0  # float              0
        self.mon_V = []  # float [2]          1:2
        self.But = 0  # U8                 3
        self.DIn = 0  # U8                 4
        self.DOut = 0  # U8                 5
        self.RGB = 0  # U8                 6
        self.DCDC_en = 0  # U8                 7
        self.DCDC_Imon = 0.0  # float              8
        self.HSen_en = 0  # U8                 9
        self.HSen_value = 0.0  # float              10
        self.PSW_en = 0  # U8                 11
        self.PSW_Vmon = []  # float [4]          12:16
        self.PSW_Imon = []  # float [3]          16:19
        self.PSW_Ifault = 0  # U8                 19

    def read_app_status(self):
        return {
            "mon_Tcpu": self.mon_Tcpu,
            "mon_V": self.mon_V,
            "But": self.But,
            "DIn": self.DIn,
            "RGB": self.RGB,
            "DCDC_en": self.DCDC_en,
            "DCDC_Imon": self.DCDC_Imon,
            "HSen_en": self.HSen_en,
            "HSen_value": self.HSen_value,
            "PSW_en": self.PSW_en,
            "PSW_Vmon": self.PSW_Vmon,
            "PSW_Imon": self.PSW_Imon,
            "PSW_Ifault": self.PSW_Ifault,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        self.parse_app_status_data()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!f ff B B B B B f B  f  B  ffff   fff   B"
        #                 0 12 3 4 5 6 7 8 9 10 11 12  15 16 17 18
        parser_str_1 = "!fffBBBBBfBfBfffffffB"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])

        self.mon_Tcpu = data_1[0]
        self.mon_V = data_1[1:3]
        self.But = data_1[3]
        self.DIn = data_1[4]
        self.DOut = data_1[5]
        self.RGB = data_1[6]
        self.DCDC_en = data_1[7]
        self.DCDC_Imon = data_1[8]
        self.HSen_en = data_1[9]
        self.HSen_value = data_1[10]
        self.PSW_en = data_1[11]
        self.PSW_Vmon = data_1[12:16]
        self.PSW_Imon = data_1[16:19]
        self.PSW_Ifault = data_1[19]

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in PMM")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in PMM")
