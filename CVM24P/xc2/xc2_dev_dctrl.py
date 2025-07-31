from .consts import XC2Addr, DeviceType
from .bus import BusBase

from .xc2_device import XC2Device


class XC2Dctrl(XC2Device):
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
            dev_type=DeviceType.Dctrl,
        )
        # self.reg_max_index = CVM_24_MAX_REG_INDEX
        # self.reg_info = CVM_32_REG_LIST
        self.off_delay = off_delay
        if min_voltage is not None:
            self.min_voltage = min_voltage
        else:
            self.min_voltage = 2.0

        if max_voltage is not None:
            self.max_voltage = min_voltage
        else:
            self.max_voltage = 13.0

    async def change_voltage(self, new_voltage: float = 0.0):
        if new_voltage > self.max_voltage or new_voltage < self.min_voltage:
            raise ValueError(f"Voltage outside range <{self.min_voltage, self.max_voltage}>")
        await self.write_reg_by_name(new_voltage, "voltageSetpoint")

    async def power_on(self):
        await self.write_reg_by_name(1, "onSwitch")

    async def power_off(self):
        await self.write_reg_by_name(self.off_delay, "offDelay")
        await self.write_reg_by_name(0, "onSwitch")
