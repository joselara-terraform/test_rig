import struct

from .consts import XC2Addr, DeviceType

from .bus import BusBase
from .xc2_except import XC2TimeoutError
from .xc2_device import XC2Device
from .consts import DeviceStatus, ProtocolEnum, PROTOCOL_ENUM_DICT


class XC2Cvm64h(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        status: DeviceStatus = DeviceStatus.Expected,
        alt_name: str = None,
        max_ttl: int = 5,
    ):
        super().__init__(
            bus,
            addr,
            status,
            alt_name,
            dev_type=DeviceType.Cvm64h,
            max_ttl=max_ttl,
        )

        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_24_REG_LIST
        self.regs = [False for _ in range(self.reg_num_of_regs)]

        self.app_status_raw = b""

        self.timestamp = 0
        self.ch_sum = 0.0
        self.v_channels: list[float] = []

    def read_app_status(self):
        return {
            "timestamp": self.timestamp,
            "ch_sum": self.ch_sum,
            "v_channels": self.v_channels,
        }

    def read_and_get_app_status(self):
        self.get_app_status()
        return self.read_app_status()

    def parse_app_status_data(self):
        """Parses packet from CVM status message"""
        parser_str_1 = "!If"

        data = self.app_status_raw
        data_1 = struct.unpack(parser_str_1, data[0 : struct.calcsize(parser_str_1)])
        self.timestamp = data_1[0]
        self.ch_sum = data_1[1]

        chan_bytes_len = int(len(data[struct.calcsize(parser_str_1) :]) / 4)
        parser_str_2 = chan_bytes_len * "f"
        data_2 = struct.unpack(parser_str_2, data[struct.calcsize(parser_str_1) :])
        self.v_channels = list(data_2)

    # def read_full_regs(self, my_addr=XC2Addr.MASTER):
    #     self.read_regs_range(my_addr=my_addr, start=0, stop=self.reg_max_index)
    # def change_protocol(self, new_protocol: ProtocolEnum):
    #     try:
    #         self.get_echo()
    #     except XC2TimeoutError:
    #         # TODO: if we have bad protocol
    #         pass
    #     else:

    def switch_to_xc2(self, my_addr=XC2Addr.MASTER) -> bool:
        last_modbus_state = PROTOCOL_ENUM_DICT[self.bus.protocol.protocol_name]
        # jsem v xc2 modu
        self.bus.change_protocol(ProtocolEnum.XC2)
        try:
            self.get_echo()  # testuju, jestli se ozve zarizeni
        except XC2TimeoutError:
            self.bus.change_protocol(ProtocolEnum.Modbus)  # pokud se neozve je moznost ze je v modbus modu, proto do nej prepneme
            try:
                self.get_echo()  # testuju jestli se zarizeni ozve v modbus modu
            except XC2TimeoutError:
                self.bus.change_protocol(last_modbus_state)  # pokud se neozve tak se neco pokazilo,
                raise Exception("Something went wrong during switching to modbus.")
            else:
                for _ in range(4):
                    try:
                        self.write_reg(data=0, index=41, req_response=True)
                    except XC2TimeoutError:
                        pass
                    try:
                        self.bus.change_protocol(ProtocolEnum.XC2)
                        self.get_echo()
                    except XC2TimeoutError:
                        self.bus.change_protocol(ProtocolEnum.Modbus)
                    else:
                        break
        self.bus.change_protocol(ProtocolEnum.XC2)
        self.store_regs()
        return True

    def switch_to_modbus(self, my_addr=XC2Addr.MASTER) -> bool:
        last_modbus_state = PROTOCOL_ENUM_DICT[self.bus.protocol.protocol_name]
        # jsem v modbus modu
        self.bus.change_protocol(ProtocolEnum.Modbus)
        try:
            self.get_echo()  # testuju, jestli se ozve zarizeni
        except XC2TimeoutError:
            self.bus.change_protocol(ProtocolEnum.XC2)  # pokud se neozve je moznost ze je v xc2 modu, proto do nej prepneme
            try:
                self.get_echo()  # testuju jestli se zarizeni ozve v xc2 modu
            except XC2TimeoutError:
                self.bus.change_protocol(last_modbus_state)  # pokud se neozve tak se neco pokazilo,
                return False  # prepneme zpet do modbus modu a koncime s chybou
            else:
                for _ in range(4):
                    try:
                        self.write_reg(data=1, index=41, req_response=True)
                    except XC2TimeoutError:
                        pass
                    try:
                        self.bus.change_protocol(ProtocolEnum.Modbus)
                        self.get_echo()
                    except XC2TimeoutError:
                        self.bus.change_protocol(ProtocolEnum.XC2)

                    else:
                        break
        self.bus.change_protocol(ProtocolEnum.Modbus)
        self.store_regs()
        return True
