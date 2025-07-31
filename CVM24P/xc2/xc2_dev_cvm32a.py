import struct

from .consts import XC2Addr, XC2Commands
from .bus import BusBase
from .xc2_except import XC2TimeoutError
from .consts import (
    ProtocolEnum,
    PROTOCOL_ENUM_DICT,
    DeviceType,
)
from .xc2_device import XC2Device
from .consts import DeviceStatus


class XC2Cvm32a(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        status: DeviceStatus = DeviceStatus.Expected,
        alt_name: str = None,
        max_ttl: int = 5,
    ):
        super().__init__(bus, addr, status, alt_name, dev_type=DeviceType.Cvm32a, max_ttl=max_ttl)
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        self.t_cpu = 0.0
        self.v_cpu = 0.0
        self.mon_36_v = 0.0
        self.mon_5_v = 0.0
        self.gpio_out = 0
        self.gpio_in = 0
        self.first_chan = 0
        self.last_chan = 0
        self.channel_sum = 0.0
        self.v_channel: list[int] = []

    def get_status(self, my_addr=XC2Addr.MASTER) -> bytes:
        """
        Send get status request and call parse function
        """
        # FIXME: does not work in CVM24
        status_data_raw: bytes = self.bus.protocol.command(my_addr, self.addr, XC2Commands.CMD_GET_STATUS)
        return status_data_raw

    def read_app_status(self):
        return {
            "t_cpu": self.t_cpu,
            "v_cpu": self.v_cpu,
            "mon_36_v": self.mon_36_v,
            "mon_5_v": self.mon_5_v,
            "gpio_out": self.gpio_out,
            "gpio_in": self.gpio_in,
            "first_chan": self.first_chan,
            "last_chan": self.last_chan,
            "channel_sum": self.channel_sum,
            "v_channel": self.v_channel,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        self.parse_app_status_data()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        # Tcou Vcpu mon36V mon5V GPIO_out GPIO_in channel_range_first channel_range_last sum_of_meas_channels
        parser_str_1 = "!ffffBBBBf"

        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])
        self.t_cpu = data_1[0]
        self.v_cpu = data_1[1]
        self.mon_36_v = data_1[2]
        self.mon_5_v = data_1[3]
        self.gpio_out = data_1[4]
        self.gpio_in = data_1[5]
        self.first_chan = data_1[6]
        self.last_chan = data_1[7]
        self.channel_sum = data_1[8]

        channel_range = self.last_chan - self.first_chan + 1
        parser_str_2 = channel_range * "h"
        data_2 = struct.unpack(parser_str_2, data[struct.calcsize(parser_str_1) :])
        self.v_channel = list(data_2)

    # def read_full_regs(self, my_addr=XC2Addr.MASTER):
    #     self.read_regs_range(my_addr=my_addr, start=0, stop=self.reg_max_index)
    # self.read_regs_range(my_addr=my_addr, start=12, stop=self.)

    def switch_to_xc2(self, my_addr=XC2Addr.MASTER) -> bool:
        last_modbus_state = PROTOCOL_ENUM_DICT[self.bus.protocol.protocol_name]
        # jsem v xc2 modu
        self.bus.change_protocol(ProtocolEnum.XC2)
        try:
            self.get_echo()  # testuju, jestli se ozve zarizeni
        except XC2TimeoutError:
            self.bus.change_protocol(ProtocolEnum.Modbus)
            # pokud se neozve je moznost ze je v modbus modu, proto do nej prepneme
            try:
                self.get_echo()  # testuju jestli se zarizeni ozve v modbus modu
            except XC2TimeoutError:
                self.bus.change_protocol(last_modbus_state)  # pokud se neozve tak se neco pokazilo,
                return False  # prepneme zpet do modbus modu a koncime s chybou
            else:
                for _ in range(4):
                    try:
                        self.write_reg(data=0, index=29, array_index=3, req_response=True)
                    except XC2TimeoutError:
                        continue
                    try:
                        self.bus.change_protocol(ProtocolEnum.XC2)
                        self.get_echo()
                    except XC2TimeoutError:
                        self.bus.change_protocol(ProtocolEnum.Modbus)
                    else:
                        break
        self.bus.change_protocol(ProtocolEnum.XC2)
        return True

    def switch_to_modbus(self, my_addr=XC2Addr.MASTER) -> bool:
        last_modbus_state = PROTOCOL_ENUM_DICT[self.bus.protocol.protocol_name]
        # jsem v modbus modu
        self.bus.change_protocol(ProtocolEnum.Modbus)
        try:
            self.get_echo()  # testuju, jestli se ozve zarizeni
        except XC2TimeoutError:
            self.bus.change_protocol(ProtocolEnum.XC2)
            # pokud se neozve je moznost ze je v xc2 modu, proto do nej prepneme
            try:
                self.get_echo()  # testuju jestli se zarizeni ozve v xc2 modu
            except XC2TimeoutError:
                self.bus.change_protocol(last_modbus_state)  # pokud se neozve tak se neco pokazilo,
                return False  # prepneme zpet do modbus modu a koncime s chybou
            else:
                # TODO: change registry change function
                # This control if register was overwriten is not safe
                for _ in range(4):
                    try:
                        self.write_reg(data=1, index=29, array_index=3, req_response=True)
                    except XC2TimeoutError:
                        continue
                    try:
                        self.bus.change_protocol(ProtocolEnum.Modbus)
                        self.get_echo()
                    except XC2TimeoutError:
                        self.bus.change_protocol(ProtocolEnum.XC2)
                    else:
                        break
        self.bus.change_protocol(ProtocolEnum.Modbus)
        return True

    def restore_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Restore registers is not implemented in CVM32A")

    def store_regs(self, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Store registers is not implemented in CVM32A")
