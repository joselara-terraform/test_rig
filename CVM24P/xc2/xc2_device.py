import asyncio
import inspect
from datetime import datetime

from .consts import (
    XC2Addr,
    XC2Commands,
    XC2SysSubcommands,
    XC2RegActionSubcommands,
    XC2RegGetInfoSubcommands,
    XC2RegFlags,
    XC2RegFlagSizeDixt,
    XC2_PARSE_TYPE_DICT,
)
from .packets import XC2Packet
from .bus import BusBase
from .xc2_except import (
    XC2TimeoutError,
    XC2DeviceNotResponding,
    UnknownDevRegStruct,
)
import struct
from copy import deepcopy

# from utils import Properties, DeviceSet
from .consts import (
    MAX_BAUD_RATE,
    NUMBER_OF_REPETITIONS,
    DeviceStatus,
    DeviceType,
)
from .utils import str_to_int, create_dev_id


class XC2Device:
    def __init__(
        self,
        bus: BusBase,
        addr=XC2Addr.DEFAULT,
        status: DeviceStatus = DeviceStatus.Expected,
        alt_name: str = None,
        dev_type: DeviceType = DeviceType.Generic,
        max_ttl: int = 5,
    ):
        """Class for accessing devices through XC2 protocol through various buses

        :param bus: Bus class for communication with device. Must be instance of BusBase
        :type bus: BusBase
        :param addr: XC2 address of the slave device, defaults to XC2Addr.DEFAULT
        :type addr: int, optional
        :param status: Communication status of the slave device, defaults to DeviceStatus.Expected
        :type status: DeviceStatus, optional
        :param alt_name: Name of the device, defaults to None. If the default option is used, the name is generated from the protocol, bus and address
        :type alt_name: str, optional
        :param dev_type: Type of the device, defaults to DeviceType.Generic
        :type dev_type: DeviceType, optional
        :param max_ttl: Maximum number of reconnect attempts till the device is considered as disconnected, defaults to 5
        :type max_ttl: int, optional
        :raises TypeError: Is raised when the bus parameter is not an instance of BusBase
        """
        if not isinstance(bus, BusBase):
            raise TypeError("Bus must be instance of BusBase.")
        self.bus = bus
        self.addr = addr
        self.status = status
        if alt_name is None:
            self.alt_name = self.get_dev_long_name()
        else:
            self.alt_name = alt_name

        self.dev_type = dev_type

        # TODO: zjistit max pkt data size a upravit hodnotu parametru
        self.max_pkt_data_size: int = 246 - 10
        # FIXME: read real max packet datasize

        # TODO: make this more readable
        self.reg_num_of_regs: int = 1
        # TODO: what it is?
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []

        self.known_regs_structure = False
        self.firmware_loading = False
        self.stay_in_bootloader = False
        self.in_bootloader = False
        self.unwanted_bootloader_counter = 15
        self.status_changed = False

        self.app_status_raw: bytes = b""
        self.id_product: str = ""
        self.id_vendor: str = ""
        self.id_version: str = ""
        self.id_custom_1: str = ""
        self.id_custom_2: str = ""

        self.__last_contact = datetime(1, 1, 1, 0, 0)
        self.__max_ttl = max_ttl
        self.__ttl = None
        self.reset_ttl()
        self.first_app_reg = 12

        # TODO: remove read full regs structure
        # self.read_full_regs_structure()

    def str_dev_type(self) -> str:
        """Returns device type as string

        :return: Device type as string
        :rtype: str
        """
        return str(self.dev_type)

    def is_echoing(self) -> bool:
        """Checks if the device is echoing.

        :return: True if the device is echoing, False otherwise
        :rtype: bool
        """
        return (
            self.status == DeviceStatus.Available
            or self.status == DeviceStatus.Timeout
            or self.status == DeviceStatus.Expected
            or self.status == DeviceStatus.Bootloader
        )

    def is_running(self) -> bool:
        """Checks if the device is running.

        :return: True if the device is running, False otherwise
        :rtype: bool
        """
        return self.status == DeviceStatus.Available or self.status == DeviceStatus.Timeout or self.status == DeviceStatus.Bootloader

    def reset_ttl(self, ttl: int = None):
        """
        Resets the TTL counter to the maximum value

        :param ttl: Amount of reconnect attempts before the device is considered as disconnected,
                    defaults to None. If the default option is used, the maximum value is used.
        :type ttl: int, optional
        """
        if ttl is None:
            self.__ttl = self.__max_ttl
            if self.known_regs_structure:
                if self.status not in [DeviceStatus.Bootloader, DeviceStatus.Available]:
                    self.status_changed = True
                if self.in_bootloader:
                    self.status = DeviceStatus.Bootloader
                else:
                    self.status = DeviceStatus.Available

        else:
            self.__ttl = ttl

    def lower_ttl(self):
        """Lowers ttl counter by one and changes device status to timeout.
        When the ttl counter reaches zero, the device status is changed to disconnected.
        If the device is resseting, the ttl counter is not changed.

        :return: Current status of the device
        :rtype: DeviceStatus
        """
        if self.status == DeviceStatus.Firmware:
            return DeviceStatus.Firmware
        if self.status == DeviceStatus.Resetting:
            return DeviceStatus.Resetting
        if self.__ttl > 1:
            self.__ttl = self.__ttl - 1
            self.status = DeviceStatus.Timeout
            self.status_changed = True
            return DeviceStatus.Timeout
        else:
            self.__ttl = 0
            self.status = DeviceStatus.Disconnected
            self.status_changed = True
            return DeviceStatus.Disconnected

    def get_ttl(self) -> int:
        """
        Returns the current value of the TTL counter.

        :return: Current value of the TTL counter
        :rtype: int
        """
        return self.__ttl

    def get_max_ttl(self):
        """Returns the maximum value of the TTL counter.

        :return: Maximum value of the TTL counter
        :rtype: int
        """
        return self.__max_ttl

    def set_last_contact(self, contact: datetime = None):
        """
        Sets the time of the last contact with the device. If the parameter is not specified, the current time is used.

        :param contact: Datetime object, defaults to None
        :type contact: datetime, optional
        """
        if contact is None:
            contact = datetime.now()
        self.__last_contact = contact

    def get_last_contact(self) -> datetime:
        """
        Returns the time of the last contact with the device.

        :return: Datetime object of the last contact with the device
        :rtype: datetime
        """
        return self.__last_contact

    def get_dev_long_name(self) -> str:
        """
        Returns the name of the device in the format ""<protocol>://<bus>/<xc2_addr>".

        :return: Name of the device
        :rtype: str
        """
        return create_dev_id(
            protocol=self.bus.protocol.protocol_name,
            bus=self.bus.bus_name,
            xc2_addr=self.addr,
        )

    def generate_format_str(self, start_index: int = 0, stop_index: int = -1, initial_read=False) -> str:
        """
        Generates string for struct pack/unpack method based on self.reg_parse_type_list
        :param start_index: Index of first reg
        :param stop_index: Index of last reg
        :return: format string
        :rtype str
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        # TODO: place all exception risen

        return "!" + "".join([parse_str for parse_str in self.reg_parse_type_list[start_index:stop_index]])

    async def get_app_status(self, my_addr=XC2Addr.MASTER):
        """
        Send get app status request and call parse function
        WARNING: request custom parse function
        :param my_addr:  Address of master device (Your PC)
        """
        try:
            self.app_status_raw = await self.bus.command(my_addr, self.addr, XC2Commands.CMD_CVM_APPSTATUS)
            self.parse_app_status_data()
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    def parse_app_status_data(self):
        """
        Parses packet from CVM status message
        !!!Needs to be replaced in inherit class!!!
        """
        raise NotImplementedError("Please implement custom function to parse app status data")

    # TODO: Type the output
    async def get_echo(self, my_addr=XC2Addr.MASTER, back_msg: bool = False):
        """
        Send echo request
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: Echo status
        """
        try:
            echo_data_raw = await self.bus.command(my_addr, self.addr, XC2Commands.CMD_ECHO, back_msg=back_msg)
            data = struct.unpack("!B", echo_data_raw)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return data[0]

    async def reset(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            await self.bus.sys_command(my_addr=my_addr, device_addr=self.addr, subcommand=XC2SysSubcommands.SYS_RESET, req_response=False)
        except Exception as e:
            self.lower_ttl()
            raise e
        if self.status != DeviceStatus.Firmware:
            self.status = DeviceStatus.Resetting
        self.known_regs_structure = False
        self.max_pkt_data_size: int = 246 - 10
        # FIXME: read real max packet datasize
        # TODO: make this more readable
        self.reg_num_of_regs: int = 1
        # TODO: what it is?
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []
        self.stay_in_bootloader = False
        self.in_bootloader = False
        return True

    async def reset_and_stay_in_bootloader(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            response = await self.bus.sys_command(
                my_addr=my_addr,
                device_addr=self.addr,
                subcommand=XC2SysSubcommands.SYS_BOOTLOADER,
            )
        except Exception as e:
            self.lower_ttl()
            raise e

        if self.status != DeviceStatus.Firmware:
            self.status = DeviceStatus.Resetting
        self.known_regs_structure = False
        self.max_pkt_data_size: int = 246 - 10
        # FIXME: read real max packet datasize
        # TODO: make this more readable
        self.reg_num_of_regs: int = 1
        # TODO: what it is?
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []
        self.stay_in_bootloader = True
        self.in_bootloader = False
        return response

    async def run_app(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            response = await self.bus.command(
                my_addr,
                self.addr,
                XC2Commands.CMD_BLCMD,
                struct.pack("!B", XC2SysSubcommands.SYS_RUNAPPL),
            )
        except Exception as e:
            # self.lower_ttl()
            raise e

        return response

    async def write_address(self, new_addr, my_addr=XC2Addr.MASTER) -> XC2Packet | bytes:
        """
        Change XC2 address of device
        :param new_addr: New address in decimal format
        :param my_addr: Address of master device (Your PC)
        :return: response byte string
        """
        if not isinstance(new_addr, int):
            raise TypeError
        if new_addr <= 0 or new_addr >= 4095:
            raise ValueError
        try:
            response: (XC2Packet | bytes) = await self.bus.sys_command(
                my_addr=my_addr,
                device_addr=self.addr,
                subcommand=XC2SysSubcommands.SYS_SETADDR,
                val=new_addr,
                val_parse_str="H",
            )
        except ValueError as e:
            raise e
        except TypeError as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        else:
            self.addr = new_addr
        self.reset_ttl()
        self.set_last_contact()
        return response

    async def read_serial_number(self, my_addr=XC2Addr.MASTER) -> tuple[str, str]:
        """
        Return device serial number and device type
        :param my_addr: Address of master device (Your PC)
        :return: tuple of device_type and device_ serial
        :rtype tuple:
        """
        try:
            response = await self.bus.sys_command(
                my_addr=my_addr,
                device_addr=self.addr,
                subcommand=XC2SysSubcommands.SYS_GETSERIAL,
            )
            device_type = response[0:5].decode("ascii")
            device_serial = response[5:].hex()

        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return device_type, device_serial

    async def write_baud_rate(self, new_baud_rate: int, my_addr=XC2Addr.MASTER) -> XC2Packet | bytes:
        """
        Sets new baud rate for the device
        :param new_baud_rate: New baud rate
        :param my_addr: Address of master device (Your PC)
        :return: System response
        """
        # TODO: must be tested, can not test at home
        try:
            if not isinstance(new_baud_rate, int):
                raise TypeError("Incorrect datatype of new baudrate.")
            if new_baud_rate <= 0 or new_baud_rate >= MAX_BAUD_RATE:
                raise ValueError(f"New baudrate too high (>{MAX_BAUD_RATE}) or too low (<0).")
            response: (XC2Packet | bytes) = await self.bus.sys_command(
                my_addr=my_addr,
                device_addr=self.addr,
                subcommand=XC2SysSubcommands.SYS_SETADDR,
                val=new_baud_rate,
                val_parse_str="I",
            )
        except ValueError as e:
            raise e
        except TypeError as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return response

    async def read_feature(self, my_addr=XC2Addr.MASTER) -> list[str]:
        """
        Gets list of ID_product, ID_vendor, ID_version, ID_custom1, ID_custom2,
        save them into member vars and returns them as list
        :param my_addr: Address of your PC
        :return: list of ID_product, ID_vendor, ID_version, ID_custom1, ID_custom2
        :rtype list:
        """
        try:
            feature_data_raw = await self.bus.command(my_addr, self.addr, XC2Commands.CMD_GET_FEATURE)
            # print("Get feature")
            # print(feature_data_raw)
            feature_raw_list = feature_data_raw.split(b"\x00")
            data: list[str] = [feature.decode("ascii") for feature in feature_raw_list][:5]
            self.id_product = data[0]
            self.id_vendor = data[1]
            self.id_version = data[2]
            self.id_custom_1 = data[3]
            self.id_custom_2 = data[4]
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return data

    # registry functions
    async def read_regs_range(
        self,
        start: int,
        stop: int,
        my_addr=XC2Addr.MASTER,
        timeout=None,
        initial_read=False,
    ):
        """
        Get data from all registry in range
        :param my_addr: Address of master device (Your PC)
        :param start: Index of first reg
        :param stop: Index of last reg
        """
        try:
            if not (self.known_regs_structure or initial_read):
                raise UnknownDevRegStruct("Read device regs structure first.")
            # input data tests
            if stop > self.reg_num_of_regs - 1:
                raise ValueError("maximum index exceeded")
            if start < 0:
                raise ValueError("start must be positive value")
            if stop < start:
                raise ValueError("start > stop")
            f_str: str = self.generate_format_str(start_index=start, stop_index=stop + 1, initial_read=initial_read)
            if struct.calcsize(f_str) > self.max_pkt_data_size:
                # split start stop range
                start_stop_list = self.split_regs_range(start, stop, initial_read=initial_read)
                # print(start_stop_list)
                for start_stop in start_stop_list:
                    if start_stop[2] is None:
                        await self.read_regs_range(
                            start=start_stop[0],
                            stop=start_stop[1],
                            my_addr=my_addr,
                            initial_read=initial_read,
                        )
                    else:
                        await self.read_reg_range(
                            index=start_stop[0],
                            start_stop_arr=start_stop[2],
                            initial_read=initial_read,
                        )
                return

            # device call
            stop += 1  # because indices
            sts_range: int = stop - start
            send_data: bytes = struct.pack("!HB", start, sts_range)
            reg_data: XC2Packet | bytes = await self.bus.command(
                my_addr=my_addr,
                device_addr=self.addr,
                data=send_data,
                command=XC2Commands.CMD_Registry_Read,
                timeout=timeout,
            )
            # print(reg_data)
            self.parse_regs_data(reg_data, start, stop, initial_read=initial_read)
        except ValueError as e:
            raise e
        except UnknownDevRegStruct as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def read_reg_range(self, index: int, start_stop_arr, my_addr=XC2Addr.MASTER, initial_read=False):
        """Get data from one register in specified range of array.

        :param index: Index of the register
        :type index: int
        :param start_stop_arr: List of tuples of start and stop indexes of array
        :type start_stop_arr: list[tuple[int, int]]
        :param my_addr: Address of master, defaults to XC2Addr.MASTER
        :type my_addr: XC2Addr | int, optional
        :raises UnknownDevRegStruct: Raised when the device registry structure is not known. It has to be read out first.
        :raises ValueError: Raised when the index is out of range
        :raises e: Raised when any other error occurs
        """
        try:
            if not (self.known_regs_structure or initial_read):
                raise UnknownDevRegStruct("Read device regs structure first.")
            if index > self.reg_num_of_regs - 1:
                raise ValueError("maximum index exceeded")
            # if start_arr < 0:
            #     raise ValueError("start must be positive value")
            # f_str = self.generate_format_str(start_index=index, stop_index=index)

            # device call
            reg_data: bytes = b""
            for start_stop in start_stop_arr:
                stop_arr = start_stop[1] + 1  # because indexes
                start_arr = start_stop[0]  # because indexes
                sts_range = stop_arr - start_arr
                send_data = struct.pack("!HHB", index, start_arr, sts_range)
                reg_data_part = await self.bus.command(
                    my_addr=my_addr,
                    device_addr=self.addr,
                    command=XC2Commands.CMD_Registry_Read,
                    data=send_data,
                )
                reg_data += reg_data_part
            self.parse_regs_data(reg_data, index, index + 1, initial_read=initial_read)
        except ValueError as e:
            raise e
        except UnknownDevRegStruct as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def read_full_regs(self, my_addr=XC2Addr.MASTER, timeout=None, initial_read=False):
        """Get data from all registry

        :param my_addr: Address of master, defaults to XC2Addr.MASTER
        :type my_addr: XC2Addr | int, optional
        :param timeout: Message timeout, defaults to None
        :type timeout: int, optional
        :param initial_read: Specifies whether it is the first readout from the device, defaults to False
        :type initial_read: bool, optional
        :raises UnknownDevRegStruct: Raised when the device registry structure is not known. It has to be read out first.
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        await self.read_regs_range(
            my_addr=my_addr,
            start=0,
            stop=self.reg_num_of_regs - 1,
            timeout=timeout,
            initial_read=initial_read,
        )

    async def read_and_get_full_regs(self, human_readable=False, timeout=None, initial_read=False):
        """
        Reads values from all registers and returns as dict by reg name or list

        :param human_readable: switching between register index and register name
        :return: dict of all reg_name:value or list
        """
        try:
            if not (self.known_regs_structure or initial_read):
                raise UnknownDevRegStruct("Read device regs structure first.")
            await self.read_full_regs(timeout=timeout, initial_read=initial_read)
            if human_readable:
                ret = {}
            else:
                ret = []
            for index in range(self.reg_num_of_regs):
                if human_readable:
                    ret[self.reg_struct_list[index]["name"]] = self.regs[index]
                else:
                    ret.append(self.regs[index])
            if not initial_read:
                self.reset_ttl()
                self.set_last_contact()
        except UnknownDevRegStruct as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        return ret

    def split_regs_range(self, start: int, stop: int, initial_read=False):
        """
        Split start stop register range to fit in XC2 packet size

        :param start: start index
        :param stop: stop index
        :return: list of start and stop indexes witch fit into XC2 packet
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        new_start = start
        new_stop = start
        start_stop_list = []
        end_on_regs = False
        while not end_on_regs:
            for index in range(new_start, stop + 1):
                if struct.calcsize(self.reg_parse_type_list[index]) > self.max_pkt_data_size:
                    new_stop = index - 1
                    start_stop_list.append((new_start, new_stop, None))
                    new_start = index
                    end_of_reg: bool = False
                    start_index: int = 0
                    reg_split_list: list[tuple] = []
                    while not end_of_reg:
                        for item_index in range(
                            start_index,
                            self.reg_struct_list[index]["array_size"],
                        ):
                            if struct.calcsize(self.reg_parse_type_list[index][start_index:item_index]) > self.max_pkt_data_size:
                                item_stop = item_index - 2
                                reg_split_list.append((start_index, item_stop))
                                # start_stop_list.append((new_start, new_start, start_index, item_stop))
                                start_index = item_index - 1
                                break
                        else:
                            item_stop = item_index
                            reg_split_list.append((start_index, item_stop))
                            start_stop_list.append((new_start, new_start, reg_split_list))
                            reg_split_list = []
                            end_of_reg = True

                    # start_stop_list.append((index, new_stop, "chyba"))
                    # print(index)
                    # print("split_regs_range_problem")
                    # start_stop_list.append((new_start, new_stop, "chyba"))
                    new_start = new_start + 1
                    new_stop = new_start
                    break
                elif (
                    self.reg_struct_list[index]["adr"] - self.reg_struct_list[new_start]["adr"]  # TODO: replace with another size count method
                ) > self.max_pkt_data_size:
                    new_stop = index - 2
                    start_stop_list.append((new_start, new_stop, None))
                    new_start = index - 1
                    break
            else:
                new_stop = stop
                start_stop_list.append((new_start, new_stop, None))
                end_on_regs = True
        for index in reversed(range(len(start_stop_list))):
            if start_stop_list[index][0] > start_stop_list[index][1]:
                start_stop_list.pop(index)
        return start_stop_list

    def parse_regs_data(self, reg_data, start: int, stop: int, initial_read: bool = False):
        """
        Extract data from input raw string from device
        :param reg_data:
        :param start: Index of first register
        :param stop: Index of last register
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        format_string = self.generate_format_str(start, stop, initial_read=initial_read)
        # print(start, stop)

        result = struct.unpack(format_string, reg_data)

        res_index: int = 0
        start_addr = self.reg_struct_list[start]["adr"]  # TODO: replace with another size count method
        for index in range(start, stop):
            if not self.reg_struct_list[index]["array"]:  # Not array register
                self.regs[index] = result[res_index]
                res_index += 1
            elif "cc" in self.reg_parse_type_list[index]:  # String register #TODO: make this better
                start_index = self.reg_struct_list[index]["adr"] - start_addr  # TODO: replace with another size count method
                stop_index = (
                    self.reg_struct_list[index]["adr"] + self.reg_struct_list[index]["array_size"] - start_addr  # TODO: replace with another size count method
                )
                raw_string = reg_data[start_index:stop_index].decode("ascii", "backslashreplace")
                self.regs[index] = raw_string.strip("\x00")
                res_index += self.reg_struct_list[index]["array_size"]
            else:  # Array register
                next_res_index = res_index + self.reg_struct_list[index]["array_size"]
                data_list = [result[i] for i in range(res_index, next_res_index)]
                self.regs[index] = data_list
                res_index = next_res_index
        # print(self.regs)

    async def write_reg(
        self,
        data,
        index: int,
        array_index=0,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        """
        Set reg in XC2Device.
        You can set up just some values in the array.
        You have to specify array_index for array register if you do not want to set up whole array

        :param req_response:
        :type data: list, int, str
        :param data: Data for the reg. For array register insert list, for value register insert value
        :param index: Index of the register
        :param array_index: Index of value in the array register
        :param my_addr: Address of master device (Your PC)
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        if index > self.reg_num_of_regs - 1:
            raise ValueError("maximum index exceeded")
        if index < 0:
            raise ValueError("start must be positive value")
        if self.reg_struct_list[index]["read_only"]:
            raise MemoryError(f"Register {self.reg_struct_list[index]['name']} is read only!")
        send_data_list: list = []
        parse_str: str = ""

        if isinstance(data, list):
            if len(data) == self.reg_struct_list[index]["array_size"] and array_index == 0:
                array_index = 0
                send_data_list = [index, array_index]
                send_data_list.extend(data)
                parse_str = "HH" + self.reg_parse_type_list[index]
            elif len(data) < self.reg_struct_list[index]["array_size"]:
                if array_index + len(data) - 1 >= self.reg_struct_list[index]["array_size"] or index < 0:
                    raise IndexError("Wrong array_index value")
                send_data_list = [index, array_index]
                send_data_list.extend(data)
                parse_str = "HH" + self.reg_parse_type_list[index][array_index : array_index + len(data)]
            else:
                raise ValueError("data is to big for reg")
        else:
            if not self.reg_struct_list[index]["array"]:
                array_index = 0
                send_data_list = [index, array_index, data]
                parse_str = "HH" + self.reg_parse_type_list[index]
            elif isinstance(data, str):
                if len(data) > self.reg_struct_list[index]["array_size"]:
                    raise ValueError("String is too long")
                send_string = data.encode("ascii")
                send_string += b"\x00" * (self.reg_struct_list[index]["array_size"] - len(data))

                array_index = 0
                send_data_list = [index, array_index]
                parse_str = "HH"
            else:
                if array_index >= self.reg_struct_list[index]["array_size"] or index < 0:
                    raise IndexError("Wrong array_index value")
                send_data_list = [index, array_index, data]
                parse_str = "HH" + self.reg_parse_type_list[index][array_index]

        if struct.calcsize(parse_str) > self.max_pkt_data_size:
            if isinstance(data, list):
                half_index = int(len(data) / 2)
                await self.write_reg(data[:half_index], index, req_response=req_response)
                await self.write_reg(data[half_index:], index, half_index, req_response=req_response)
                return data
            else:
                raise OverflowError("Unable to write register this long.")

        send_data: bytes = b""
        for item, char in zip(send_data_list, parse_str):
            send_data += struct.pack(f"!{char}", item)

        if isinstance(data, str):
            send_data += send_string

        await self.bus.command(
            my_addr=my_addr,
            device_addr=self.addr,
            command=XC2Commands.CMD_Registry_Write,
            data=send_data,
            req_response=req_response,
        )
        if req_response:
            if isinstance(self.regs[index], list):
                if array_index == 0:
                    self.regs[index][array_index] = data
                else:
                    if isinstance(data, list):
                        len_data = len(data)
                        end_index = array_index + len_data
                        self.regs[index] = self.regs[index][:array_index] + data + self.regs[index][end_index:]
                    else:
                        len_data = 1
                        end_index = array_index + len_data
                        self.regs[index] = self.regs[index][:array_index] + [data] + self.regs[index][end_index:]
            else:
                self.regs[index] = data
        return data

    async def write_reg_str(
        self,
        data_str,
        index,
        array_index=0,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        """
        Parse data string based on register data type and write it to the register.

        :param data_str: String to be parsed and written to the register
        :type data_str: str
        :param index: Register index
        :type index: int
        :param array_index: Specifies the array index if the register is an array, defaults to 0
        :type array_index: int, optional
        :param my_addr: XC2 address of master, defaults to XC2Addr.MASTER
        :type my_addr: int, optional
        :param req_response: Signalizes if response from the device is requested, defaults to True
        :type req_response: bool, optional
        """
        data = self.parse_data_str(data_str, index)
        if data is not None:
            ret_data = await self.write_reg(data, index, array_index, my_addr, req_response)
            return ret_data

    def parse_data_str(self, data_str, index):
        """
        Parse data string to data type based on specific register datatype.

        :param data_str: String to be parsed
        :type data_str: str
        :param index: Register index
        :type index: int
        :raises UnknownDevRegStruct: Raised when the device registry structure is not known. It has to be read out first.
        :return: Parsed value
        :rtype: int | float | str | list
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        array = self.reg_struct_list[index]["array"]
        mod = self.reg_struct_list[index]["mod"]
        if array:
            if mod == XC2RegFlags.FL_CH:  # string
                # parse just string
                # find invalid chars
                value = data_str.encode("ascii", "ignore").decode()
            elif mod == XC2RegFlags.FL_FE:  # float/enum
                # parse array of float
                value = self.parse_list(data_str, float)
            elif mod == XC2RegFlags.FL_U or mod == XC2RegFlags.FL_I:  # int
                # parse array of ints
                value = self.parse_list(data_str, int)
            else:
                value = None
        else:
            if mod == XC2RegFlags.FL_CH:  # is there something like that
                value = data_str.encode("ascii", "ignore").decode()
            elif mod == XC2RegFlags.FL_FE:  # float/enum
                value = float(data_str)
            elif mod == XC2RegFlags.FL_U or mod == XC2RegFlags.FL_I:  # int
                value = str_to_int(str(data_str))
                # parse array of ints
            else:
                value = None

        return value

    @staticmethod
    def parse_list(self, value_str, value_type):
        """Parses string to list of values.

        :param value_str: String to be parsed into list
        :type value_str: str
        :param value_type: Type of the values in the list
        :type value_type: int | float (could be potentially anything else)
        :return: List of parsed values
        :rtype: list
        """
        if value_str[0] != "[" or value_str[-1] != "]":
            return
        else:
            value_list = [value_type(x) for x in value_str.replace("[", "").replace("]", "").split(",")]
            return value_list

    async def write_all_regs_default(self, all_registry=True, my_addr=XC2Addr.MASTER):
        """Set all registers to default values.

        :param all_registry: defaults to True
        :type all_registry: bool, optional
        :param my_addr: Address of master, defaults to XC2Addr.MASTER
        :type my_addr: int, optional
        """
        if all_registry:
            how = 1
        else:
            how = 0
        data = struct.pack("!BB", int(XC2RegActionSubcommands.RegistryAction_SetDefaults), how)
        await self.bus.command(
            my_addr=my_addr,
            device_addr=self.addr,
            command=XC2Commands.CMD_Registry_Action,
            data=data,
        )

    def get_reg_by_index(self, index):
        """
        Read indexed register.
        You have to get registry value previously!

        :return Registry value
        """
        return self.regs[index]

    def get_reg_by_name(self, name: str):
        """
        Read register based on name.
        You have to get registry value previously!

        :type name: str
        :return: Registry value
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                return self.regs[index]
        raise ValueError(f"No such register: {name}")

    async def read_reg_by_name(self, name: str):
        """
        Read register based on name.
        You have to get registry value previously!

        :type name: str
        :return: Registry value
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                await self.read_regs_range(start=index, stop=index)
                return True
        return False

    async def read_reg_by_index(self, index: int):
        """
        Read register based on index.
        You have to get registry value previously!

        :type index: int
        :return: Registry value
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        try:
            await self.read_regs_range(start=index, stop=index)
            return True
        except Exception as e:
            raise e

    def reg_name_to_index(self, name: str) -> int | bool:
        """
        Convert register name to index

        :param name: The name of the register
        :type name: str
        :return: The index of the register if found, False otherwise
        :rtype: int | bool
        :raises UnknownDevRegStruct: If the device register structure is unknown
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                return index
        return False

    async def get_regs_size(self, my_addr=XC2Addr.MASTER, initial_read: bool = False):
        """
        Get regs info size

        :param my_addr: Address of master device (Your PC)
        :return data: tuple (number_of_registers, number_of_bytes)
        :rtype: tuple
        """
        try:
            reg_data = await self.bus.command(
                my_addr=my_addr,
                device_addr=self.addr,
                command=XC2Commands.CMD_Registry_GetInfo,
                data=struct.pack("!B", XC2RegGetInfoSubcommands.RegistryInfo_Size),
            )
            data = struct.unpack("!HH", reg_data)
            self.reg_num_of_regs = data[0]
            self.reg_num_of_bytes = data[1]
        except Exception as e:
            self.lower_ttl()
            raise e
        if not initial_read:
            self.reset_ttl()
            self.set_last_contact()
        return data

    async def get_regs_structure(self, start_index: int, stop_index: int, my_addr=XC2Addr.MASTER, initial_read=False):
        """
        Gets structure of registers from reg from start_index to stop_index (includes)

        :param start_index: index of first register
        :param stop_index: index of last register
        :param my_addr: Address of master device (Your PC)
        """
        # test data test
        if stop_index > self.reg_num_of_regs - 1:
            raise ValueError("maximum index exceeded")
        if start_index < 0:
            raise ValueError("start must be positive value")
        if stop_index < start_index:
            raise ValueError("start > stop")
        try:
            num_of_regs = stop_index - start_index + 1
            # TODO: max index control
            regs_raw_data = await self.bus.command(
                my_addr=my_addr,
                device_addr=self.addr,
                command=XC2Commands.CMD_Registry_GetInfo,
                data=struct.pack(
                    "!BHB",
                    XC2RegGetInfoSubcommands.RegistryInfo_Structure,
                    start_index,
                    num_of_regs,
                ),
            )
        except ValueError as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        if not initial_read:
            self.reset_ttl()
            self.set_last_contact()
        # VERY BAD IDEA... PROBLEM WITH 0x0 and char "0" 0x30 in some cases (0x0 0x30) -> 0x000
        # regs_raw_list = re.split(b"([0-9,A-Z,a-z,_]{2,32}\x00)", regs_raw_data)
        # FIXME: nazev registru musi byt alespon 2 znaky nebo se to rozbije
        # TODO: přidat podporu pro min,max
        real_num_of_regs = 0
        while True:
            last_byte_index = 4
            reg_dict = {}
            reg_index, flags = (
                struct.unpack("!h", regs_raw_data[0:2])[0],
                struct.unpack("!h", regs_raw_data[2:4])[0],
            )
            flags_arr = flags & XC2RegFlags.FL_ARR == XC2RegFlags.FL_ARR
            flags_bnd = flags & XC2RegFlags.FL_BND == XC2RegFlags.FL_BND
            flags_hex = flags & XC2RegFlags.FL_HEX == XC2RegFlags.FL_HEX
            flags_ro = flags & XC2RegFlags.FL_RO == XC2RegFlags.FL_RO
            flags_val = flags & XC2RegFlags.FL_VAL == XC2RegFlags.FL_VAL

            if flags_bnd:
                raise NotImplementedError("Flag_BND and min,max values are not implemented")

            if flags_arr:
                reg_data = regs_raw_data[0:6]
                last_byte_index = 6
                array_size = struct.unpack("!H", reg_data[4:6])[0]
                reg_dict["array_size"] = array_size

            else:
                reg_data = regs_raw_data[0:4]
                reg_dict["array_size"] = 1  # 1?

            reg_name = ""
            while regs_raw_data[last_byte_index] != 0:
                reg_name += chr(regs_raw_data[last_byte_index])
                last_byte_index += 1
            last_byte_index += 1

            reg_dict["idx"] = reg_index

            reg_dict["adr"] = None  # musi se spocitat nasledovne
            # reg_struct_list.append(reg_struct[1])
            reg_dict["name"] = reg_name
            # reg_struct_list.append(reg_name)

            flags_type = flags & XC2RegFlags.FL_MASK_TYPE
            # reg_struct_list.append(XC2RegFlagsDict[flags_type])
            reg_dict["type"] = flags_type
            flags_mod = flags & XC2RegFlags.FL_MASK_MOD
            reg_dict["mod"] = flags_mod
            # reg_struct_list.append(XC2RegFlagsDict[flags_mod])

            reg_dict["array"] = flags_arr
            reg_dict["bound"] = flags_bnd
            reg_dict["hex"] = flags_hex
            reg_dict["read_only"] = flags_ro
            reg_dict["volatile"] = flags_val

            # reg_struct_list.extend([flags_arr, flags_bnd, flags_hex, flags_ro, flags_val])

            self.reg_struct_list[reg_index] = deepcopy(reg_dict)
            regs_raw_data = regs_raw_data[last_byte_index:]
            real_num_of_regs += 1
            if len(regs_raw_data) == 0:
                break
        # If we cannot read all registry at once, we recursively call function
        if num_of_regs > real_num_of_regs:
            start_index = reg_index + 1
            await self.get_regs_structure(start_index, stop_index)

    async def read_reg_structure(self, index, my_addr=XC2Addr.MASTER):
        """
        Get reg info of one register
        !!! Don't use it !!!
        !!! Use get_regs_info_structure() instead !!

        :param index: Index of register
        :param my_addr: Address of master device (Your PC)
        """
        try:
            # device call
            reg_data = await self.bus.command(
                my_addr=my_addr,
                device_addr=self.addr,
                command=XC2Commands.CMD_Registry_GetInfo,
                data=struct.pack(
                    "!BHB",
                    XC2RegGetInfoSubcommands.RegistryInfo_Structure,
                    index,
                    1,
                ),
            )

            data = list(struct.unpack("!BBH", reg_data[0 : struct.calcsize("!BBH")]))

            # flags_type = data[2] & XC2RegFlags.FL_MASK_TYPE
            # flags_mod = data[2] & XC2RegFlags.FL_MASK_MOD
            flags_arr = data[2] & XC2RegFlags.FL_ARR == XC2RegFlags.FL_ARR
            # flags_bnd = data[2] & XC2RegFlags.FL_BND == XC2RegFlags.FL_BND
            # flags_hex = data[2] & XC2RegFlags.FL_HEX == XC2RegFlags.FL_HEX
            # flags_ro = data[2] & XC2RegFlags.FL_RO == XC2RegFlags.FL_RO
            # flags_val = data[2] & XC2RegFlags.FL_VAL == XC2RegFlags.FL_VAL
            if flags_arr:
                array_size = struct.unpack(
                    "!H",
                    reg_data[struct.calcsize("!BBH") : struct.calcsize("!BBHH")],
                )[0]
                data.append(array_size)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    def create_parse_type_list(self):
        """
        Create list of parse strings based on current registry structure
        """
        self.reg_parse_type_list = []

        for reg in self.reg_struct_list:
            self.reg_parse_type_list.append(XC2_PARSE_TYPE_DICT[reg["mod"]][reg["type"]] * reg["array_size"])

    async def read_full_regs_structure(self, initial_read: bool = False):
        """
        Set of methods to get full registry structure
        """
        for _ in range(NUMBER_OF_REPETITIONS):
            try:
                await self.get_regs_size(initial_read=initial_read)
            except XC2TimeoutError:
                pass
            else:
                break
        else:
            print(self.addr, "Module not inicialized")
            raise XC2DeviceNotResponding(f"{self.addr} device is not responding")
            pass

        self.clear_regs_structure()
        # FIXME: do this to work with modbus
        for _ in range(NUMBER_OF_REPETITIONS + 20):
            for index in range(self.reg_num_of_regs + 1):
                if self.reg_struct_list[index] == {}:
                    break
            try:
                # print(index)
                await self.get_regs_structure(index, self.reg_num_of_regs - 1, initial_read=initial_read)
            except XC2TimeoutError:
                pass
            else:
                break
        else:
            pass
            # gen_console_output_direct(
            #     write_on_console_sig=self.write_on_console_sig,
            #     text=f'<div style= "color: red; font: bold;">{NUMBER_OF_REPETITIONS}th try</div>',
            #     flag="SYSTEM"
            # )
        fcn_list_2 = [
            self.count_regs_address,
            self.create_parse_type_list,
            self.read_regs_default_value,
        ]
        for fcn in fcn_list_2:
            for _ in range(NUMBER_OF_REPETITIONS):
                try:
                    ret = fcn()
                    if inspect.iscoroutine(ret):
                        await ret
                except XC2TimeoutError:
                    pass
                else:
                    break
            else:
                pass

        # self.known_regs_structure = True  # if there were no problem
        self.regs = [False for _ in range(self.reg_num_of_regs)]

    def print_full_regs_structure(self):
        """
        Method for debuging to print out registry structure
        """
        print(*self.reg_struct_list, sep="\n")
        # print(sys.getsizeof(self.reg_struct_list))

    def print_all_regs_value(self):
        """
        Method for debuging to print out registry structure
        """
        print(*self.regs, sep="\n")
        # print(sys.getsizeof(self.reg_struct_list))

    async def read_reg_default_value(self, index, my_addr=XC2Addr.MASTER):
        """
        Read default value of register

        :param index: Index of register
        :type index: int
        :param my_addr: Address of master, defaults to XC2Addr.MASTER
        :type my_addr: int, optional
        """
        # if struct.calcsize(self.reg_parse_type_list[index]) > self.max_pkt_data_size:
        #     index_list = self.split_reg(index)
        #     regs_raw_data = b""
        #     for item_index in index_list:
        #         regs_raw_data_part = await self.bus.command(
        #             my_addr=my_addr,
        #             device_addr=self.addr,
        #             command=XC2Commands.CMD_Registry_GetInfo,
        #             data=struct.pack(
        #                 "!BHH", XC2RegGetInfoSubcommands.RegistryInfo_DefaultValue, index, item_index
        #             ),
        #         )
        #         regs_raw_data += regs_raw_data_part
        #
        # else:
        try:
            regs_raw_data: XC2Packet | bytes = await self.bus.command(
                my_addr=my_addr,
                device_addr=self.addr,
                command=XC2Commands.CMD_Registry_GetInfo,
                data=struct.pack(
                    "!BH",
                    XC2RegGetInfoSubcommands.RegistryInfo_DefaultValue,
                    index,
                ),
            )
            if len(regs_raw_data) < struct.calcsize("!" + self.reg_parse_type_list[index]):
                start_index = int(len(regs_raw_data) / struct.calcsize("!" + self.reg_parse_type_list[index][1]))
                for item_index in range(start_index, self.reg_struct_list[index]["array_size"]):
                    regs_raw_data_part = await self.bus.command(
                        my_addr=my_addr,
                        device_addr=self.addr,
                        command=XC2Commands.CMD_Registry_GetInfo,
                        data=struct.pack(
                            "!BHH",
                            XC2RegGetInfoSubcommands.RegistryInfo_DefaultValue,
                            index,
                            item_index,
                        ),
                    )
                    regs_raw_data += regs_raw_data_part
            # Parse data
            if "cc" in self.reg_parse_type_list[index]:
                data = regs_raw_data.strip(b"\x00").decode("utf-8")
            else:
                data = struct.unpack("!" + self.reg_parse_type_list[index], regs_raw_data)
                if not self.reg_struct_list[index]["array"]:
                    data = data[0]
            self.reg_struct_list[index]["default"] = data
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def read_regs_default_value(self):
        """Gets all registry default values from Device"""
        for reg_index in range(self.reg_num_of_regs):
            await self.read_reg_default_value(reg_index)

    def get_reg_default_value(self, reg_index: int):
        """
        This function is used to read the default registry value by its index.

        :param reg_index: index of register.
        :return: default value of register.
        """
        if reg_index > self.reg_num_of_regs:
            raise IndexError("Wrong array_index value")
        return self.reg_struct_list[reg_index]["default"]

    def get_reg_default_value_by_name(self, reg_name: str):
        """
        This function is used to read the default registry value by its name.

        :param reg_name: name of register.
        :return: default value of register.
        """
        for reg_index in range(self.reg_num_of_regs):
            if self.reg_struct_list[reg_index]["name"] == reg_name:
                return self.reg_struct_list[reg_index]["default"]
        raise ValueError(f"No such register: {reg_name}")

    async def write_reg_default_value(self, reg_index: int):
        """
        This function is used to write the default registry value by its index.

        :param reg_index: index of register.
        :return: default value of register.
        """
        try:
            value = self.get_reg_default_value(reg_index)
            ret_val = await self.write_reg(value, reg_index)
            return ret_val
        except Exception as e:
            raise e

    async def write_reg_default_value_by_name(self, reg_name: str):
        """
        This function is used to write the default registry value by its name.

        :param reg_name: name of register.
        :return: default value of register.
        """
        try:
            value = self.get_reg_default_value_by_name(reg_name)
            ret_val = await self.write_reg_by_name(value, reg_name)
            return ret_val
        except Exception as e:
            raise e

    def split_reg(self, index):
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        start = 0
        index_list = []
        # end_on_reg = False
        parse_str: str = self.reg_parse_type_list[index]
        index_list.append(start)
        for parse_type_index in range(len(parse_str)):
            if struct.calcsize(parse_str[start:parse_type_index]) > self.max_pkt_data_size:
                index_list.append(parse_type_index - 1)
                start = parse_type_index
        return index_list

    def count_regs_address(self):
        """Count address in bytes of each register"""
        last_addr = 0
        for reg in self.reg_struct_list:
            if reg == {}:
                raise Exception("A register isn't initialized")
                # TODO: exception
                # return False
            reg["adr"] = last_addr
            last_addr += XC2RegFlagSizeDixt[reg["type"]] * reg["array_size"]

    def clear_regs_structure(self):
        """
        Clear registry structure object and inicialize it with empty object
        """
        self.reg_struct_list = [{}] * self.reg_num_of_regs

    async def read_and_get_reg(self, index):
        await self.read_regs_range(start=index, stop=index)
        return self.regs[index]

    async def read_and_get_reg_by_name(self, name):
        ret = await self.read_reg_by_name(name)
        if not ret:
            raise ValueError(f"No such register: {name}")
        return self.get_reg_by_name(name)

    async def write_reg_by_name(
        self,
        data,
        name: str,
        array_index=0,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        """Write register value based on name.

        :param data: Data to be written
        :type data: int | float | str | list
        :param name: Name of register
        :type name: str
        :param array_index: If the register datatype is an array, specify index of written value, defaults to 0
        :type array_index: int, optional
        :param my_addr: Address of master, defaults to XC2Addr.MASTER
        :type my_addr: int, optional
        :param req_response: Signalizes if response from the device is requested, defaults to True
        :type req_response: bool, optional
        :raises UnknownDevRegStruct: Raised when the device registry structure is not known
        :raises ValueError: Raised when the register name is not found
        :return: 0 if the write_reg method was called successfully
        :rtype: int
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                try:
                    ret_data = await self.write_reg(data, index, array_index, my_addr, req_response)
                except Exception as e:
                    raise e
                return ret_data
        raise ValueError("No such register")

    async def restore_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        """
        Restore register from eeprom

        :param my_addr: Address of master device (Your PC)
        :return: Device response
        """
        try:
            data = struct.pack("!B", int(XC2RegActionSubcommands.RegistryAction_Restore))
            response: bytes = await self.bus.command(my_addr, self.addr, XC2Commands.CMD_Registry_Action, data)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return response

    async def store_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        """
        Restore register to non-volatile memory

        :param req_response:
        :param my_addr: Address of master device (Yaour PC)
        :return: Device response
        """
        try:
            data: bytes = struct.pack("!B", int(XC2RegActionSubcommands.RegistryAction_StoreToEeprom))
            response: bytes = await self.bus.command(my_addr, self.addr, XC2Commands.CMD_Registry_Action, data)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return response

    async def initial_structure_reading(self):
        """
        Read full registry structure and default values. Used in initial device setup.
        """
        await self.read_full_regs_structure(initial_read=True)
        await self.read_and_get_full_regs(initial_read=True)
        self.known_regs_structure = True
        await asyncio.sleep(0)  # if there were no problem
        self.reset_ttl()

    async def read_and_get_app_status(self):
        """
        Read app status from device. This method must be implemented in child class.
        :raises NotImplementedError: Raised when the method is not implemented in child class
        """
        raise NotImplementedError("This XC2Device does not have app status")

    async def power_enable(self):
        """
        Enable power on device. This method must be implemented in child class.
        :raises NotImplementedError: Raised when the method is not implemented in child class
        """
        raise NotImplementedError("This XC2Device does not have power_enable")

    def get_dev_status(self) -> DeviceStatus:
        """
        Get device status.
        :return: Device status
        :rtype: DeviceStatus
        """
        return self.status

    def set_dev_status(self, status: DeviceStatus):
        """
        Set device status.
        :param status: Device status
        :type status: DeviceStatus
        """
        self.status = status

    def get_num_of_regs(self):
        """
        Get number of registers in device.
        :return: Number of registers in device
        :rtype: int
        """
        return self.reg_num_of_regs

    def get_reg_struct_list(self):
        """
        Get list of registers structure.
        :return: List of registers structure
        :rtype: list[dict]
        """
        return self.reg_struct_list

    def get_reg_structure(self, index: int):
        """
        Get structure of one register by index.
        :param index: Index of the register
        :type index: int
        :raises ValueError: Raised when the index is out of range
        :return: Structure of the register
        :rtype: dict
        """
        if index < 0 or index > self.reg_num_of_regs - 1:
            raise ValueError(f"No such register: {index}")
        return self.reg_struct_list[index]

    def get_reg_structure_by_name(self, name: str):
        """
        Get structure of one register by name.
        :param name: Name of the register
        :type name: str
        :raises ValueError: Raised when the name is not found
        :return: Structure of the register
        :rtype: dict
        """
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                return self.reg_struct_list[index]
        raise ValueError(f"No such register: {name}")

    def get_regs_range(self, start, stop):
        """
        Get registers contents in range from start to stop (includes).
        :param start: Index of first register
        :type start: int
        :param stop: Index of last register
        :type stop: int
        :return: List of registers contents
        :rtype: list
        """
        return self.regs[start : stop + 1]
