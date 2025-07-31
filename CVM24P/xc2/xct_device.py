import logging
import json
from datetime import datetime
from .xc2_dev_evm8 import DataBuffer

from .consts import (
    XC2Addr,
    XCTPacketType,
    XC2Commands,
    XC2SysSubcommands,
    XCTCommands,
    XC2RegGetInfoSubcommands,
    XC2RegFlags,
    XC2RegFlagSizeDixt,
    XC2_PARSE_TYPE_DICT,
    XCTRecordChannel,
    XCTVChannel,
)
from .packets import XCTPacket
from .bus import BusBase, TCPBus
from .xc2_except import (
    XC2TimeoutError,
    UnknownDevRegStruct,
)
from .xct_except import XCTError
import struct
from copy import deepcopy

# from utils import Properties, DeviceSet
from .consts import (
    DeviceStatus,
    DeviceType,
)
from .utils import create_dev_id, record_channel_mask_to_list
import re
import asyncio


def is_float(string: str):
    if "." not in string:
        return False
    try:
        float(string)
        return True
    except ValueError:
        return False


def retype_value(value_str: str):
    if "," in value_str:
        if value_str.startswith("["):
            value_str = value_str[1:]
        if value_str.endswith("]"):
            value_str = value_str[:-1]

        items = value_str.split(",")
        val = []
        for item in items:
            val.append(retype_value(item.strip()))
    elif value_str.startswith("0x"):
        val = int(value_str, 0)
    elif is_float(value_str):
        val = float(value_str)
    elif value_str.lstrip("-").isdigit():
        val = int(value_str)
    elif value_str.lower() == "true":
        val = True
    elif value_str.lower() == "false":
        val = False
    else:
        return value_str
    return val


class XCTDevice:
    def __init__(
        self,
        bus: BusBase,
        alt_name: str,
        addr=XC2Addr.DEFAULT,
        status: DeviceStatus = DeviceStatus.Expected,
        dev_type: DeviceType = DeviceType.Generic,
        max_ttl: int = 5,
    ):
        """param bus - xc2bus which is the device connected to"""
        if not isinstance(bus, BusBase):
            raise TypeError("Bus must be instance of BusBase.")
        self.bus = bus
        self.addr = addr
        self.status = status
        self.dev_type = dev_type
        self.alt_name = alt_name

        # TODO: zjistit max pkt data size a upravit hodnotu parametru
        self.max_pkt_data_size: int = 1500
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

        self.first_app_reg = 0

        self.__last_contact = datetime(1, 1, 1, 0, 0)
        self.__max_ttl = max_ttl
        self.__ttl = None
        self.reset_ttl()

        # TODO: remove read full regs structure
        # self.read_full_regs_structure()

    def str_dev_type(self):
        return str(self.dev_type)

    def is_echoing(self) -> bool:
        return (
            self.status == DeviceStatus.Available
            or self.status == DeviceStatus.Timeout
            or self.status == DeviceStatus.Expected
            or self.status == DeviceStatus.Bootloader
        )

    def is_running(self) -> bool:
        return self.status == DeviceStatus.Available or self.status == DeviceStatus.Timeout or self.status == DeviceStatus.Bootloader

    def reset_ttl(self, ttl: int = None):
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
        return self.__ttl

    def get_max_ttl(self):
        return self.__max_ttl

    def set_last_contact(self, contact: datetime = None):
        if contact is None:
            contact = datetime.now()
        self.__last_contact = contact

    def get_last_contact(self):
        return self.__last_contact

    def get_dev_long_name(self) -> str:
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
        raise NotImplementedError("Not implemented in XCT Device")

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
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.DEVICE,
            dst=self.alt_name,
            src=my_addr,
            cmd=XCTCommands.GET,
            data="FWStatus",
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, back_msg=back_msg, return_pkt=True)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        if ret.cmd == XCTCommands.ERROR:
            logging.error(f"{ret.data}")
            return 0
        data = ret.data
        if data == "True":
            data = "20"
        try:
            data = int(data)
        except ValueError:
            return 0
        if data == "":
            return 0
        if int(data) >= 20:
            return 2
        elif int(data) >= 10:
            return 1
        return 0

    async def reset(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def reset_and_stay_in_bootloader(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def run_app(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def write_address(self, new_addr, my_addr=XC2Addr.MASTER) -> XCTPacket | bytes:
        """
        Change XC2 address of device
        :param new_addr: New address in decimal format
        :param my_addr: Address of master device (Your PC)
        :return: response byte string
        """
        raise NotImplementedError("Not implemented in XCT Device")

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

    async def write_baud_rate(self, new_baud_rate: int, my_addr=XC2Addr.MASTER) -> XCTPacket | bytes:
        """
        Sets new baud rate for the device
        :param new_baud_rate: New baud rate
        :param my_addr: Address of master device (Your PC)
        :return: System response
        """
        # TODO: must be tested, can not test at home
        raise NotImplementedError("Not implemented in XCT Device")

    async def read_feature(self, my_addr=XC2Addr.MASTER) -> list[str]:
        """c
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
            for reg in self.reg_struct_list[start:stop]:
                reg_name = reg["name"]
                await self.read_reg_by_name(reg_name, initial_read)
        except ValueError as e:
            raise e
        except UnknownDevRegStruct as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def read_reg_range(self, index: int, start_stop_arr, my_addr=XC2Addr.MASTER):
        try:
            if not self.known_regs_structure:
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
            self.parse_regs_data(reg_data, index, index + 1)
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
                    self.reg_struct_list[index]["adr"]
                    - self.reg_struct_list[new_start]["adr"]
                    # TODO: replace with another size count method
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

    def parse_regs_data(self, reg_data, name: str = None, index: int = None, initial_read: bool = False):
        """
        Extract data from input raw string from device
        :param reg_data:
        :param name: Name of register
        :param index: Or index of register
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        if name is None and index is None:
            raise ValueError("You must specify name or index of parsed register")

        if name is not None:
            index = self.reg_name_to_index(name, initial_read)
            if isinstance(index, bool) and not index:
                raise ValueError(f"No such register {name}")

        reg_struct = self.reg_struct_list[index]
        if reg_struct["array"]:
            reg_data = reg_data[1:-1]

        reg_data = retype_value(reg_data)
        self.regs[index] = reg_data

    async def write_reg(
        self,
        data,
        index: int,
        array_index: int = None,
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

        reg_name = self.reg_struct_list[index]["name"]

        ret = await self.write_reg_by_name(data, reg_name, array_index=array_index, my_addr=my_addr, req_response=req_response)

        return ret

    async def write_reg_str(
        self,
        data_str,
        index,
        array_index=0,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        raise NotImplementedError("Not implemented in XCT_device")

    @staticmethod
    def parse_list(self, value_str, value_type):
        if value_str[0] != "[" or value_str[-1] != "]":
            return
        else:
            value_list = [value_type(x) for x in value_str.replace("[", "").replace("]", "").split(",")]
            return value_list

    async def write_all_regs_default(self, all_registry=True, my_addr=XC2Addr.MASTER):
        raise NotImplementedError("Not implemented in XCT Device")

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

    async def read_reg_by_name(self, name: str, initial_read: bool = False):
        """
        Read register based on name.
        You have to get registry value previously!

        :type name: str
        :return: Registry value
        """
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.DEVICE,
            dst=self.alt_name,
            src=XC2Addr.MASTER,
            cmd=XCTCommands.GET,
            data=name,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt)
        except Exception:
            self.lower_ttl()
            return False
        self.reset_ttl()
        self.set_last_contact()
        self.parse_regs_data(ret, name=name, initial_read=initial_read)
        return True

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

    def reg_name_to_index(self, name: str, initial_read: bool = False) -> int | bool:
        """Convert register name to index

        Args:
            name (str): register name

        Returns:
            int | bool: index of register, False if not found
        """
        if not (self.known_regs_structure or initial_read):
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                return index
        return False

    async def get_regs_size(self, my_addr=XC2Addr.MASTER):
        """
        Get regs info size

        :param my_addr: Address of master device (Your PC)
        :return data: tuple (number_of_registers, number_of_bytes)
        :rtype: tuple
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def get_regs_structure(self, start_index: int, stop_index: int, my_addr=XC2Addr.MASTER):
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
        raise NotImplementedError("Not implemented in XCT Device")

    def create_parse_type_list(self):
        """
        Create list of parse strings based on current registry structure
        """
        self.reg_parse_type_list = []

        for reg in self.reg_struct_list:
            self.reg_parse_type_list.append(XC2_PARSE_TYPE_DICT[reg["mod"]][reg["type"]] * reg["array_size"])

    async def read_full_regs_structure(self):
        """
        Set of methods to get full registry structure
        """
        use_name = self.alt_name
        if self.alt_name == "PTC":
            use_name = "kg"
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.DEVICE,
            dst=self.alt_name,
            src=XC2Addr.MASTER,
            cmd=XCTCommands.REST,
            data=f"GET devices/ptc/hw/{use_name}",
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
        except Exception as e:
            self.lower_ttl()
            raise e
        try:
            json_ret = json.loads(ret.data)
        except json.decoder.JSONDecodeError:
            raise XCTError("Unable to parse device registry structure")
        regs = json_ret["reg"]
        self.reg_num_of_regs = len(regs)
        self.reg_num_of_bytes = len(ret.data)
        self.clear_regs_structure()

        for ind in range(len(self.reg_struct_list)):
            reg_name = list(regs.keys())[ind]
            from_json = regs[reg_name]
            self.regs.append(from_json)

            is_array = isinstance(from_json, list)
            array_size = 1
            if is_array:
                array_size = len(from_json)
            self.reg_struct_list[ind] = {
                "adr": ind,
                "array": is_array,
                "array_size": array_size,
                "bound": False,
                "default": 0,
                "hex": False,
                "idx": ind,
                "mod": 0,
                "name": reg_name,
                "read_only": False,
                "type": 4,
                "volatile": True,
            }

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
        Gets default value of register based on index

        :param index:
        :param my_addr:
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def read_regs_default_value(self):
        """Gets all registry default values from Device"""
        raise NotImplementedError("Not implemented in XCT Device")

    def get_reg_default_value(self, reg_index: int):
        """
        This function is used to read the default registry value by its index.

        :param reg_index: index of register.
        :return: default value of register.
        """
        raise NotImplementedError("Not implemented in XCT Device")

    def get_reg_default_value_by_name(self, reg_name: str):
        """
        This function is used to read the default registry value by its name.

        :param reg_name: name of register.
        :return: default value of register.
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def write_reg_default_value(self, reg_index: int):
        """
        This function is used to write the default registry value by its index.

        :param reg_index: index of register.
        :return: default value of register.
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def write_reg_default_value_by_name(self, reg_name: str):
        """
        This function is used to write the default registry value by its name.

        :param reg_name: name of register.
        :return: default value of register.
        """
        raise NotImplementedError("Not implemented in XCT Device")

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
        print(index_list)
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
        self.regs = []
        self.reg_struct_list = [{}] * self.reg_num_of_regs

    async def read_and_get_reg(self, index):
        name = self.reg_struct_list[index]["name"]
        await self.read_reg_by_name(name)
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
        array_index: int = None,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")

        if array_index is None:
            msg_data = f"{name} {data}"
        else:
            msg_data = f"{name}[{array_index}] {data}"

        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.DEVICE,
            dst=self.alt_name,
            src=my_addr,
            cmd=XCTCommands.SET,
            data=msg_data,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=req_response)
            if not ret.cmd == XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except XCTError as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return data

    async def restore_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        """
        Restore register from eeprom

        :param my_addr: Address of master device (Your PC)
        :return: Device response
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def store_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        """
        Restore register to non-volatile memory

        :param req_response:
        :param my_addr: Address of master device (Yaour PC)
        :return: Device response
        """
        raise NotImplementedError("Not implemented in XCT Device")

    async def initial_structure_reading(self):
        await self.read_full_regs_structure()
        await self.read_and_get_full_regs(initial_read=True)
        self.known_regs_structure = True  # if there were no problem
        self.reset_ttl()

    async def read_and_get_app_status(self):
        raise NotImplementedError("Not implemented in XCT Device")

    async def power_enable(self):
        raise NotImplementedError("Not implemented in XCT Device")

    def get_dev_status(self):
        return self.status

    def set_dev_status(self, status: DeviceStatus):
        self.status = status

    def get_num_of_regs(self):
        return self.reg_num_of_regs

    def get_reg_struct_list(self):
        return self.reg_struct_list

    def get_reg_structure(self, index: int):
        if index < 0 or index > self.reg_num_of_regs - 1:
            raise ValueError(f"No such register: {index}")
        return self.reg_struct_list[index]

    def get_reg_structure_by_name(self, name: str):
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                return self.reg_struct_list[index]
        raise ValueError(f"No such register: {name}")

    def get_regs_range(self, start, stop):
        return self.regs[start : stop + 1]


class XCTClient:
    def __init__(
        self,
        bus: TCPBus,
    ):
        self.bus = bus
        self._read_data_buffer = DataBuffer()
        self._read_data_channels: list = []
        self._read_data_channels_mask: int = 0
        self._downloading: bool = False
        self._acq_channel_count: int = 0
        self._next_read_data_index: int = 0
        self._reading: bool = False

    async def get_echo(self):
        """
        Send echo request
        :return data[0]: Echo status
        """
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            cmd=XCTCommands.ECHO,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except XC2TimeoutError:
            return False
        except Exception as e:
            raise e
        return True

    async def get_msg(self, parameter):
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=parameter,
            cmd=XCTCommands.GET,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except Exception as e:
            raise e

        return retype_value(ret.data)

    async def set_msg(self, parameter, value):
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=f"{parameter} {value}",
            cmd=XCTCommands.SET,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except Exception as e:
            raise e
        return True

    async def start_eis(
        self,
        start_frequency: float | int,
        stop_frequency: float | int,
        points_per_decade: int,
        max_amp_voltage: float,
        max_amp_current: float,
        v_range: int = 1,
        i_range: int = 1,
        periods: int = 5,
        samples: int = 1024,
        v_channel: int = 2,
        start_read: bool = True,
    ):
        gain_list_val = [0.1, 1, 10]
        if v_range in gain_list_val:
            v_range = gain_list_val.index(v_range)
        if i_range in gain_list_val:
            i_range = gain_list_val.index(i_range)

        data_str = (
            f"startEIS2 {start_frequency} {stop_frequency} {points_per_decade} {max_amp_voltage} "
            f"{max_amp_current} {v_range} {i_range} {periods} {samples} {v_channel}"
        )

        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=data_str,
            cmd=XCTCommands.PLAIN_CMD,
        )
        try:
            # raw_bytes = self.bus.protocol.pkt_to_bytes(req_pkt)
            # print(raw_bytes)
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
            record_channels = ["Z", "Phi", "Re", "Im", "genFreq", "sampleRate", "ampV", "ampI", "ampGen"]
            await self.clear_read_buffer()
            self._acq_channel_count = len(record_channels)
            self._read_data_channels = record_channels
            self._read_data_channels_mask = 0xFFF
            if start_read:
                await self._start_read_data()
        except Exception as e:
            raise e
        return True

    async def start_cv(
        self,
        voltage_chanel: XCTVChannel,
        record_channels: list[XCTRecordChannel],
        voltage_start: float | int,
        voltage_margin1: float | int,
        voltage_margin2: float | int,
        voltage_end: float | int,
        speed: float | int,
        sweep: float | int,
        start_read: bool = True,
    ):
        record_mask = 0
        for chan in record_channels:
            record_mask += chan.value
        if not record_mask:
            raise ValueError("No record channel specified")
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=f"startCV {voltage_chanel.value} {record_mask} {voltage_start} {voltage_margin1} {voltage_margin2} {voltage_end} {speed} {sweep}",
            cmd=XCTCommands.PLAIN_CMD,
        )
        try:
            raw_bytes = self.bus.protocol.pkt_to_bytes(req_pkt)
            print(raw_bytes)
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
            await self.clear_read_buffer()
            self._acq_channel_count = len(record_channels)
            self._read_data_channels = record_channel_mask_to_list(record_mask)
            self._read_data_channels_mask = record_mask
            if start_read:
                await self._start_read_data()
        except Exception as e:
            raise e
        return True

    async def start_ca(
        self,
        voltage_chanel: XCTVChannel,
        record_channels: list[XCTRecordChannel],
        current_start: float | int,
        current_margin1: float | int,
        current_margin2: float | int,
        current_end: float | int,
        speed: float | int,
        sweep: float | int,
        start_read: bool = True,
    ):
        record_mask = 0
        for chan in record_channels:
            record_mask += chan.value
        if not record_mask:
            raise ValueError("No record channel specified")
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=f"startCA {voltage_chanel.value} {record_mask} {current_start} {current_margin1} {current_margin2} {current_end} {speed} {sweep}",
            cmd=XCTCommands.PLAIN_CMD,
        )
        try:
            # raw_bytes = self.bus.protocol.pkt_to_bytes(req_pkt)
            # print(raw_bytes)
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
            await self.clear_read_buffer()
            self._acq_channel_count = len(record_channels)
            self._read_data_channels = record_channel_mask_to_list(record_mask)
            self._read_data_channels_mask = record_mask
            if start_read:
                await self._start_read_data()
        except Exception as e:
            raise e
        return True

    async def start_time_scan(self, record_channels: list[XCTRecordChannel], every_n_sample: int, avg_last_m: int, start_read: bool = True):
        """
        m<=n
        """ ""
        record_mask = 0
        for chan in record_channels:
            record_mask += chan.value
        if not record_mask:
            raise ValueError("No record channel specified")
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=f"startTimeScan {record_mask} {every_n_sample} {avg_last_m}",
            cmd=XCTCommands.PLAIN_CMD,
        )
        try:
            # raw_bytes = self.bus.protocol.pkt_to_bytes(req_pkt)
            # print(raw_bytes)
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
            await self.clear_read_buffer()
            self._acq_channel_count = len(record_channels)
            self._read_data_channels = record_channel_mask_to_list(record_mask)
            self._read_data_channels_mask = record_mask
            if start_read:
                await self._start_read_data()
        except Exception as e:
            raise e
        return True

    async def stop_acq(self):
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data="stopAcq",
            cmd=XCTCommands.PLAIN_CMD,
        )

        try:
            # raw_bytes = self.bus.protocol.pkt_to_bytes(req_pkt)
            # print(raw_bytes)
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except Exception as e:
            raise e
        return True

    async def read_buffer_cmd(self):
        print(f"PTC_READING_BUFFER: {self._next_read_data_index}")
        req_pkt = self.bus.protocol.create_pkt(
            pkt_type=XCTPacketType.SERVER,
            dst=XC2Addr.DEFAULT,
            src=XC2Addr.MASTER,
            data=f"ReadBuffer {self._next_read_data_index}",
            cmd=XCTCommands.PLAIN_CMD,
        )
        try:
            ret: XCTPacket = await self.bus.send_pkt_with_response(req_pkt, return_pkt=True)
            if ret.cmd != XCTCommands.OK:
                raise XCTError(f"{ret.data}")
        except Exception as e:
            raise e
        try:
            if ret.data == "True" or ret.data == "False":
                await asyncio.sleep(1)
                return 0
            parsed = re.findall("(\d+) ", ret.data)[0]
            channel_count = int(parsed[0])
            if self._acq_channel_count != channel_count:
                await self.stop_acq()
                await self.clear_read_buffer()
                raise XCTError(f"Last started scan and Read Buffer has different channels lenght: {channel_count}")

            data = ret.data[(len(parsed[0])) :].strip()
            data = data.replace(" ", ",")

            data = retype_value(data)
            it = [iter(data)] * self._acq_channel_count
            data = list(map(list, zip(*it)))
            self._next_read_data_index += len(data)
        except Exception as e:
            print(f"ERR_DATA: {ret.data}")
            raise e

        self._read_data_buffer.add_data(data)

    async def check_downloading(self):
        self._downloading = await self.get_msg("downloading")
        return self._downloading

    async def _get_acq_len(self):
        return await self.get_msg("acqLen")

    async def _reading_rutine(self, sleep_before: int = 1000):
        await asyncio.sleep(sleep_before / 1000)
        while True:
            try:
                await self.check_downloading()
                await self.read_buffer_cmd()
                await asyncio.sleep(0.1)
            except Exception as e:
                if (not self._downloading) and "ERROR 44" in str(e):
                    print("PTC_READING_BUFFER DONE")
                    break
                elif "ERROR 44" in str(e):
                    await asyncio.sleep(1)
                    continue
                logging.error(e)
                self.clear_read_buffer()
                raise e
        self._reading = False

    async def _start_read_data(self):
        self._reading = True
        asyncio.create_task(self._reading_rutine())

    async def clear_read_buffer(self):
        self._read_data_channels = 0
        self._downloading = False
        self._acq_channel_count = 0
        self._next_read_data_index = 0
        self._reading = False
        await asyncio.sleep(0.5)
        self._read_data_buffer.clear_data()

    async def read_buffer(self) -> dict:
        if self._read_data_buffer.has_data():
            data = []
            while self._read_data_buffer.has_data():
                tmp = self._read_data_buffer.get_data()
                for dat in tmp:
                    data.append(dat)
            return {"status": "data", "channels": self._read_data_channels, "data": data}
        return {"status": "empty_buffer"}

    def read_buffer_done(self):
        return (not self._reading) and (not self._read_data_buffer.has_data())

    def set_reading(self, status: bool):
        self._reading = status

    def get_reading(self) -> bool:
        return self._reading
