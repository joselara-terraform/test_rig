import struct

from .consts import XC2Addr, XC2Commands, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Xam(XC2Device):
    def __init__(self, bus: BusBase, addr=XC2Addr.DEFAULT, alt_name: str = None, max_ttl: int = 5):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Xam)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        # registr                data type in C      index in data1 app status
        self.out_ctrl = 0  # U8                 0
        self.pwm = []  # U8 [8]             1:9
        self.output_status = []  # U8 [8]             9:17
        self.out_sense = []  # float [8]           17:25
        self.in_di = 0  # U8                 25
        self.in_ai = []  # float [8]          26:34
        self.XP_mode = []  # U8 [4]             34:38
        self.XP_V = []  # float [4]          38:42
        self.XP_value = []  # float [4]          42:46
        self.Cjc_T = [
            0.0,
            0.0,
        ]  # float [2]          46    #Only second walue is send with app status
        self.mon_Tcpu = 0.0  # float              47
        self.mon_V = []  # float [3]          48:51

    def read_app_status(self):
        return {
            "out_ctrl": self.out_ctrl,
            "pwm": self.pwm,
            "output_status": self.output_status,
            "out_sense": self.out_sense,
            "in_di": self.in_di,
            "in_ai": self.in_ai,
            "XP_mode": self.XP_mode,
            "XP_V": self.XP_V,
            "XP_value": self.XP_value,
            "Cjc_T%1": self.Cjc_T[1],
            "mon_Tcpu": self.mon_Tcpu,
            "mon_V": self.mon_V,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        self.parse_app_status_data()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!B  BBBB.BBBB   BBBB.BBBB   ffff.ffff   B   ffff.ffff    BBBB   ffff   ffff   f  f  fff"
        #                 0  1       8   9       16 17       24 25  26       33  34  37 38  41 42  45 46 47 49 51
        parser_str_1 = "!BBBBBBBBBBBBBBBBBffffffffBffffffffBBBBfffffffffffff"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])

        self.out_ctrl = data_1[0]
        self.pwm = data_1[1:9]
        self.output_status = data_1[9:17]
        self.out_sense = data_1[17:25]
        self.in_di = data_1[25]
        self.in_ai = data_1[26:34]
        self.XP_mode = data_1[34:38]
        self.XP_V = data_1[38:42]
        self.XP_value = data_1[42:46]
        self.Cjc_T[1] = data_1[46]
        # Attention Cjc_T is field of two floats but only one is send with this method
        self.mon_Tcpu = data_1[47]
        self.mon_V = data_1[48:]

    def parse_app_fuse_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!B  BBBB.BBBB   BBBB.BBBB   ffff.ffff   B   ffff.ffff    BBBB   ffff   ffff   f  f  fff"
        #                 0  1       8   9       16 17       24 25  26       33  34  37 38  41 42  45 46 47 49 51
        parser_str_1 = "!BBBBBBB"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])
        self.output_status = data_1[0:]

    def send_app_readwrite(self, index: int, what: int, my_addr=XC2Addr.MASTER):
        """
        Send app readwrite command 0xA1
        :param my_addr:  Address of master device (Your PC)
        :param index which IO you want control
        :param what 0=clr, 1=set, 2=toggle
        """
        send_data = struct.pack("!BB", index, what)
        self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_XAM_APPREADWRITE, data=send_data)
        self.parse_app_status_data()

    def send_app_readwrite_all(self, out_ctrl: int, pwm_list: list, my_addr=XC2Addr.MASTER):
        """
        Send app readwrite command 0xA2
        :param my_addr:  Address of master device (Your PC)
        :param out_ctrl sets corresponding register
        :param pwm_list [0,50,100...] sets pwm duty cycle
        """
        pwm_list.insert(0, out_ctrl)
        if not all(isinstance(x, int) for x in pwm_list):
            raise TypeError
        self.app_status_raw = self.bus.protocol.command(
            my_addr,
            self.addr,
            XC2Commands.CMD_XAM_APPREADWRITE_ALL,
            data=bytes(pwm_list),
        )
        self.parse_app_status_data()

    def send_app_fuses(self, what: int, disable_mask: int = 0, my_addr=XC2Addr.MASTER):
        """
        Send app readwrite command 0xB0
        :param my_addr:  Address of master device (Your PC)
        :param what 0=read, 1=reset, 2=disable by mask
        :disable_mask 1-255, bit per fuse
        """
        if what == 0:
            send_data = struct.pack("!B", what)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_XAM_APPFUSES, data=send_data)
            self.parse_app_fuse_data()
        elif what == 1:
            send_data = struct.pack("!B", what)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_XAM_APPFUSES, data=send_data)
        elif what == 2:
            send_data = struct.pack("!BB", what, disable_mask)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_XAM_APPFUSES, data=send_data)

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in XAM")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in XAM")
