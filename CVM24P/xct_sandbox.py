# Warning To run this demo. This file has to be in parent folder.

from xc2.bus import TCPBus
from xc2.consts import ProtocolEnum
from xc2.xct_device import XCTDevice, XCTClient
import asyncio


async def main():
    ip_addr_m = "127.0.0.1"
    port_m = 20006
    alt_name = "PTC"
    bus = TCPBus(ip_addr_m, port_m, ProtocolEnum.XCT)
    await bus.connect()
    device = XCTDevice(bus, alt_name)
    echo = await device.get_echo()
    print(f"ECHO: {echo}")
    await device.initial_structure_reading()
    print(f"before: {device.get_reg_by_name('adc_value')}")
    await asyncio.sleep(0.5)
    reg = await device.read_and_get_reg_by_name("adc_value")
    print(f"adc_value: {reg}")
    await asyncio.sleep(0.5)
    reg = await device.read_and_get_reg(39)
    print(f"index: {reg}")

    old = await device.read_and_get_reg_by_name("fw_fuse_safe")
    print(f"fw_fuse_safe: {old}")
    print(f"changing to {[-6, 6, -6, 6, -6, 6, -20, -20, 1, 1]}")
    await device.write_reg_by_name([-6, 6, -6, 6, -6, 6, -20, -20, 1, 1], "fw_fuse_safe")
    await asyncio.sleep(5)
    print(f"change: {await device.read_and_get_reg_by_name('fw_fuse_safe')}")
    await device.write_reg_by_name(old, "fw_fuse_safe")
    await asyncio.sleep(1)
    print(f"back: {await device.read_and_get_reg_by_name('fw_fuse_safe')}")

    # ATTENTION INDEXES DO NOT CORRESPOND TO XC2 INDEXES 30 PTC is setPoint 66 in XC2
    # await device.write_reg(1, 30)
    # await asyncio.sleep(5)
    # await device.write_reg(0, 30)

    client = XCTClient(bus)
    print(f"ECHO: {await client.get_echo()}")
    i = await client.get_msg("I")
    print(f"GET I: {i}")

    print("Setting setpoint 1")
    ret = await client.set_msg("setpoint", 1)
    print(f"set: {ret}")
    await asyncio.sleep(5)
    print("Setting setpoint 0")
    await client.set_msg("setpoint", 0)

    # START EIS
    # await client.start_eis(
    #     start_frequency=1,
    #     stop_frequency=10_000,
    #     points_per_decade=10,
    #     max_amp_voltage=0.01,
    #     max_amp_current=1,
    # )

    # START CV
    # await client.start_cv(
    #     XCTFeedbackChannel.Vref,
    #     [XCTRecordChannel.Vout, XCTRecordChannel.Vref, XCTRecordChannel.Vsense, XCTRecordChannel.I],
    #     voltage_start=0.4167,
    #     voltage_margin1=0.40,
    #     voltage_margin2=0.42,
    #     voltage_end=0.4167,
    #     speed=10,
    #     sweep=5,
    # )

    # START CA
    # await client.start_ca(
    #     XCTFeedbackChannel.Vout,
    #     [XCTRecordChannel.Vout, XCTRecordChannel.Vref, XCTRecordChannel.Vsense, XCTRecordChannel.I],
    #     current_start=4.167,
    #     current_margin1=4.0,
    #     current_margin2=4.2,
    #     current_end=4.167,
    #     speed=10,
    #     sweep=5
    # )

    # START Time Scan
    # await client.start_time_scan(
    #     [XCTRecordChannel.Vout, XCTRecordChannel.Vref, XCTRecordChannel.Vsense, XCTRecordChannel.I],
    #     every_n_sample=5,
    #     avg_last_m=5,
    # )


if __name__ == "__main__":
    asyncio.run(main())
