from .consts import XC2Addr, DeviceType
from .bus import BusBase
from .xc2_dev_evm8 import XC2Evm8


class XC2Evm8Core(XC2Evm8):
    def __init__(self, bus: BusBase, addr=XC2Addr.DEFAULT, alt_name: str = None, max_ttl: int = 5):
        super().__init__(bus, addr, alt_name=alt_name, max_ttl=max_ttl, dev_type=DeviceType.Evm8Core)

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

    async def power_enable(self, status: int = 1):
        """Powering on HVLOADS and EVMs"""
        await self.write_reg_by_name(status, "core_power_en_hvload")
        await self.write_reg_by_name(status, "core_power_en_evm")

    async def set_setpoint_dc(self, setpoint: int | float, ramp_sec: int | float = None, autotune: bool = True):
        if ramp_sec is None:
            if setpoint > 5:
                ramp_sec = 2 * setpoint
            else:
                ramp_sec = 10.0
        await self.write_reg_by_name(ramp_sec, "core_setpoint_ramp_amps_sec")
        await self.write_reg_by_name(1, "core_hvload_status")
        await self.write_reg_by_name(setpoint, "core_setpoint_dc")
        await self.write_reg_by_name(int(autotune), "core_setpoint_autotune_en")
        await self.write_reg_by_name(0, "core_fb")
        leds_cur = await self.read_reg_by_name("core_front_panel_leds")
        await self.write_reg_by_name(leds_cur | 0xC, "core_front_panel_leds")

    async def set_setpoint_cv(self, setpoint: int | float, max_i: int | float, probe: int = 1, ramp_sec: int | float = None, pid: list = [1.0, 10.0, 0]):
        if ramp_sec is None:
            ramp_sec = 1000.0
        if probe == 0 or probe > 3:
            ValueError("Probe must be between 1 and 3")
        await self.write_reg_by_name(pid, "core_pid_const")
        await self.write_reg_by_name(3 * [ramp_sec], "core_setpoint_ramp_volts_sec")
        await self.write_reg_by_name(3 * [max_i], "core_setpoint_dc_U_limit_I_max")
        await self.write_reg_by_name(1, "core_hvload_status")
        await self.write_reg_by_name(1, "core_hvload_status")
        await self.write_reg_by_name(setpoint, "core_setpoint_dc_U", array_index=probe - 1)
        await self.write_reg_by_name(probe, "core_fb")
        leds_cur = await self.read_reg_by_name("core_front_panel_leds")
        await self.write_reg_by_name(leds_cur | 0xC, "core_front_panel_leds")

    async def zero_current(self, ramp_sec: int | float = 1000.0):
        await self.write_reg_by_name(0xC, "core_front_panel_leds")
        await self.write_reg_by_name(5, "core_hvload_status")
        await self.write_reg_by_name(1, "core_ac_out_stop")
        await self.write_reg_by_name(0, "core_setpoint_freq")
        await self.write_reg_by_name(0, "core_setpoint_ac")
        await self.write_reg_by_name(ramp_sec, "core_setpoint_ramp_amps_sec")
        await self.write_reg_by_name(0, "core_ac_out_stop")
        await self.write_reg_by_name(0, "core_setpoint_dc")
        await self.write_reg_by_name(0, "core_setpoint_autotune_en")
        leds_cur = await self.read_reg_by_name("core_front_panel_leds")
        await self.write_reg_by_name(leds_cur | 0xC, "core_front_panel_leds")
