from .consts import XC2Addr, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Hvload(XC2Device):
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        alt_name: str = None,
        max_ttl: int = 5,
        min_voltage: float = None,
        max_voltage: float = None,
        off_delay: int = 500,
    ):
        super().__init__(
            bus,
            addr,
            alt_name=alt_name,
            max_ttl=max_ttl,
            dev_type=DeviceType.Hvload,
        )
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.first_app_reg = 11
