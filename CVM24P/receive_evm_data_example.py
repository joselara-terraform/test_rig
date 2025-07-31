import asyncio

from xc2.xc2_dev_evm8 import XC2Evm8
from xc2.bus import TCPBus
from xc2.consts import ProtocolEnum, DeviceStatus


async def main():
    ip_addr_m = "10.11.2.11"
    xc2_addr_m = 0x11
    port_m = 17001
    bus = TCPBus(ip_addr_m, port_m, ProtocolEnum.XC2)
    await bus.connect()
    device_m = XC2Evm8(bus, xc2_addr_m, status=DeviceStatus.Available)
    await device_m.initial_structure_reading()
    await device_m.start_data_socket()

    try:
        while True:
            if device_m.evm_data_buffer.has_data():
                print(device_m.evm_data_buffer.get_data())
            await asyncio.sleep(0)
    except KeyboardInterrupt:
        pass
    finally:
        device_m.evm_receive_stop()


if __name__ == "__main__":
    asyncio.run(main())
