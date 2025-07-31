import struct

from .consts import XC2Addr, XC2Commands, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Dio(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        alt_name: str = None,
        max_ttl: int = 5,
    ):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Dio)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        # registr                data type in C      index in data1 app status
        self.out_ctrl = 0  # U8                 0
        self.in_v = 0  # U8                 1
        self.out_sense = []  # float [8]          2:10
        self.in_di = 0  # U8                 10
        self.in_ai = []  # float [4]          11:15
        self.mon_V = []  # float [5]          15:20
        self.output_status = []  # U8 [8]             20:28
        self.in_value = []  # float [4]          28:32
        self.out_value = []  # float [8]          32:

    def get_status(self, my_addr=XC2Addr.MASTER):
        """
        Send get status request and call parse function
        """
        # FIXME: does not work in CVM24
        status_data_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_GET_STATUS)
        return status_data_raw

    def read_app_status(self):
        return {
            "out_ctrl": self.out_ctrl,
            "in_v": self.in_v,
            "out_sense": self.out_sense,
            "in_di": self.in_di,
            "in_ai": self.in_ai,
            "mon_V": self.mon_V,
            "output_status": self.output_status,
            "in_value": self.in_value,
            "out_value": self.out_value,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        self.parse_app_status_data()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channel
        # parser_str_1 = "!B  B ffff.ffff   B   ffff   fffff   BBBB.BBBB   ffff   ffff.ffff"
        #                 0  1 2       9  10  11  14 15   19 20       27 28  31 32       39
        parser_str_1 = "!BBffffffffBfffffffffBBBBBBBBffffffffffff"
        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])

        self.out_ctrl = data_1[0]
        self.in_v = data_1[1]
        self.out_sense = data_1[2:10]
        self.in_di = data_1[10]
        self.in_ai = data_1[11:15]
        self.mon_V = data_1[15:20]
        self.output_status = data_1[20:28]
        self.in_value = data_1[28:32]
        self.out_value = data_1[32:]

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
        self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_DIO_APPREADWRITE, data=send_data)
        self.parse_app_status_data()

    def send_app_readwrite_all(self, out_ctrl: int, out_value: list, my_addr=XC2Addr.MASTER):
        """
        Send app readwrite command 0xA1
        :param my_addr:  Address of master device (Your PC)
        :param out_ctrl sets corresponding register
        :param out_value [0,50,100...] sets out_value MUST BE FLOTS
        """
        print("Pozor nelze ovládat první output!!!!")
        if not all(isinstance(x, float) for x in out_value):
            raise TypeError
        out_value.insert(0, out_ctrl)
        send_data = struct.pack("!B" + str(len(out_value[1:])) + "f", *out_value)
        self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_DIO_APPREADWRITE_ALL, data=send_data)
        self.parse_app_status_data()

    def send_app_fuses(self, what: int, disable_mask: int = 0, my_addr=XC2Addr.MASTER):
        """
        Send app readwrite command 0xA1
        :param my_addr:  Address of master device (Your PC)
        :param what 0=read, 1=reset, 2=disable by mask
        :disable_mask 1-255, bit per fuse
        """
        if what == 0:
            send_data = struct.pack("!B", what)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_DIO_APPFUSES, data=send_data)
            self.parse_app_fuse_data()
        elif what == 1:
            send_data = struct.pack("!B", what)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_DIO_APPFUSES, data=send_data)
        elif what == 2:
            send_data = struct.pack("!BB", what, disable_mask)
            self.app_status_raw = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_DIO_APPFUSES, data=send_data)

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in CVM32A")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in CVM32A")
