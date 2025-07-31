from .bus_virtual import VirtualBus
from .consts import (
    XC2Addr,
    XC2RegFlags,
    XC2RegFlagSizeDixt,
    XC2_PARSE_TYPE_DICT,
)
from .packets import XC2Packet
from .xc2_device import XC2Device
from .xc2_except import (
    UnknownDevRegStruct,
)
from copy import deepcopy

# from utils import Properties, DeviceSet
from .consts import (
    DeviceStatus,
    DeviceType,
)
from .utils import str_to_int


class XC2VirtualDevice(XC2Device):
    def __init__(
        self,
        bus: VirtualBus,  # TODO: virtual bus
        virtual_dev_dict: dict,
        parent_dev_dict: dict,
        copy_parent: str = None,
        addr=XC2Addr.DEFAULT,
        status: DeviceStatus = DeviceStatus.Expected,
        alt_name: str = None,
        dev_type: DeviceType = DeviceType.Virtual,
        max_ttl: int = 5,
    ):
        """param bus - xc2bus which is the device connected to"""
        super().__init__(bus, addr, status, alt_name, dev_type=dev_type, max_ttl=max_ttl)
        self.copy_parent = copy_parent
        self.virtual_reg_dict = virtual_dev_dict
        # t_shunt_ohm:
        #       parent_name: HV_LOAD1
        #       reg: mes_temp
        #       index: 8
        #     t_shunt_water_out:
        #       parent_name: HV_LOAD1
        #       reg: mes_temp
        #       index: 9
        #     shunt_water_flow:
        #       parent_name: HV_LOAD2
        #       reg: io_in_value
        #       index: 0
        self.reg_name_list = []
        for reg_name in virtual_dev_dict:
            self.reg_name_list.append(reg_name)
        self.parent_dict = parent_dev_dict
        # {"alt_name": device}
        self.check_device_list()
        self.copy_parent_num_of_regs = 0
        self.first_app_reg = 0
        self.fill_virtual_parent_buses()

    def fill_virtual_parent_buses(self):
        for key in self.parent_dict:
            parent_bus_name = self.parent_dict[key].bus.bus_name
            if parent_bus_name not in self.bus.parent_buses:
                self.bus.parent_buses.append(parent_bus_name)

    def check_device_list(self):
        for key in self.virtual_reg_dict:
            parent_name = self.virtual_reg_dict[key]["parent_name"]
            device = self.parent_dict.get(parent_name)
            if device is None:
                raise ValueError(f"Missing device {parent_name} in parent_dev_list parameter")

    def is_echoing(self) -> bool:
        is_echoing = True
        for alt_name in self.parent_dict:
            is_echoing = is_echoing and self.parent_dict[alt_name].is_echoing()
        return is_echoing

    def is_running(self) -> bool:
        is_running = self.status == DeviceStatus.Available or self.status == DeviceStatus.Timeout or self.status == DeviceStatus.Bootloader
        for alt_name in self.parent_dict:
            is_running = is_running and self.parent_dict[alt_name].is_running()
        return is_running

    def parents_running(self) -> bool:
        is_running = True
        for alt_name in self.parent_dict:
            is_running = is_running and self.parent_dict[alt_name].is_running()
        return is_running

    # Init functions
    async def read_full_regs_structure(self, initial_read: bool = False):
        """
        Set of methods to get full registry structure
        """
        for dev_name in self.parent_dict:
            if not self.parent_dict[dev_name].known_regs_structure:
                await self.parent_dict[dev_name].read_full_regs_structure(initial_read=initial_read)

        # if self.copy_parent is not None:
        #     self.add_copy_parent_to_reg_structure()

        await self.get_regs_size()
        self.clear_regs_structure()
        await self.get_regs_structure(0, self.reg_num_of_regs - 1)
        self.count_regs_address()

        self.create_parse_type_list(),
        await self.read_regs_default_value(),

        # self.known_regs_structure = True  # if there were no problem
        self.regs = [False for _ in range(self.reg_num_of_regs)]

    async def get_regs_size(self, my_addr=XC2Addr.MASTER, initial_read: bool = False):
        """
        Get regs info size

        :param my_addr: Address of master device (Your PC)
        :return data: tuple (number_of_registers, number_of_bytes)
        :rtype: tuple
        """

        if self.copy_parent is not None:
            self.reg_num_of_regs = len(self.reg_name_list) + self.parent_dict[self.copy_parent].get_num_of_regs()
            self.copy_parent_num_of_regs = self.parent_dict[self.copy_parent].get_num_of_regs()  # TODO: check if necessary
        else:
            self.reg_num_of_regs = len(self.reg_name_list)
            self.reg_num_of_copy_parent_regs = 0

    def clear_regs_structure(self):
        """
        Clear registry structure object and inicialize it with empty object
        """
        self.reg_struct_list = [{}] * self.reg_num_of_regs

    async def get_regs_structure(self, start_index: int, stop_index: int, my_addr=XC2Addr.MASTER, initial_read: bool = False):
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

        index = 0
        if self.copy_parent is not None:
            copy_parent_reg_struct_list = self.parent_dict[self.copy_parent].get_reg_struct_list()
            for index in range(len(copy_parent_reg_struct_list)):
                self.reg_struct_list[index] = deepcopy(copy_parent_reg_struct_list[index])
            index += 1

        for virtual_reg_name in self.reg_name_list:
            dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
            reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
            arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
            arr_range = self.virtual_reg_dict[virtual_reg_name].get("arr_range")
            device = self.parent_dict[dev_name]
            reg_index = device.reg_name_to_index(reg_name)
            if arr_index is not None:
                self.reg_struct_list[index] = deepcopy(device.reg_struct_list[reg_index])
                self.reg_struct_list[index]["array_size"] = 1
                self.reg_struct_list[index]["array"] = False
                self.reg_struct_list[index]["default"] = list(self.reg_struct_list[index]["default"])[arr_index]

            elif arr_range is not None:
                start = int(arr_range[: arr_range.index("-")])
                stop = int(arr_range[arr_range.index("-") + 1 :])
                self.reg_struct_list[index] = deepcopy(device.reg_struct_list[reg_index])
                self.reg_struct_list[index]["array_size"] = stop + 1
                self.reg_struct_list[index]["array"] = False
                self.reg_struct_list[index]["default"] = list(self.reg_struct_list[index]["default"])[start : stop + 1]
            else:
                self.reg_struct_list[index] = deepcopy(device.reg_struct_list[reg_index])
                if isinstance(self.reg_struct_list[index]["default"], tuple):
                    self.reg_struct_list[index]["default"] = list(self.reg_struct_list[index]["default"])
                else:
                    self.reg_struct_list[index]["default"] = self.reg_struct_list[index]["default"]

            self.reg_struct_list[index]["name"] = virtual_reg_name
            self.reg_struct_list[index]["idx"] = index
            index += 1

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

    def create_parse_type_list(self):
        """
        Create list of parse strings based on current registry structure
        """
        self.reg_parse_type_list = []

        for reg in self.reg_struct_list:
            self.reg_parse_type_list.append(XC2_PARSE_TYPE_DICT[reg["mod"]][reg["type"]] * reg["array_size"])

    async def read_regs_default_value(self):
        """Gets all registry default values from Device"""
        for reg_index in range(self.copy_parent_num_of_regs, self.reg_num_of_regs):
            await self.read_reg_default_value(reg_index)

    # XC2 Commands
    async def read_app_status(self):
        return "Virtual device has no APP status"

    async def get_app_status(self, my_addr=XC2Addr.MASTER):
        """
        Send get app status request and call parse function
        WARNING: request custom parse function
        :param my_addr:  Address of master device (Your PC)
        """
        try:
            for alt_name in self.parent_dict:
                await self.parent_dict[alt_name].get_app_status(my_addr=my_addr)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def get_echo(self, my_addr=XC2Addr.MASTER, back_msg: bool = False):
        """
        Send echo request
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: Echo status
        """
        response_list = []
        try:
            for alt_name in self.parent_dict:
                response_list.append(await self.parent_dict[alt_name].get_echo(my_addr=my_addr))
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

        contains_1 = False
        contains_2 = False

        for response in response_list:
            if response == 1:
                contains_1 = True
            elif response == 2:
                contains_2 = True

            if contains_1 and contains_2:
                return 0

        if contains_1:
            return 1
        elif contains_2:
            return 2
        else:
            return 0

    async def reset(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            for alt_name in self.parent_dict:
                await self.parent_dict[alt_name].reset(my_addr=my_addr)
        except Exception as e:
            self.lower_ttl()
            raise e

        for alt_name in self.parent_dict:
            status = self.parent_dict[alt_name].get_dev_status()
            if status != DeviceStatus.Firmware:
                self.parent_dict[alt_name].set_dev_status(DeviceStatus.Resetting)
        if self.status != DeviceStatus.Firmware:
            self.status = DeviceStatus.Resetting
        self.known_regs_structure = False

        self.reg_num_of_regs: int = 1
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []
        self.stay_in_bootloader = False
        self.in_bootloader = False
        return None

    async def reset_and_stay_in_bootloader(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            for alt_name in self.parent_dict:
                await self.parent_dict[alt_name].reset_and_stay_in_bootloader(my_addr=my_addr)
        except Exception as e:
            self.lower_ttl()
            raise e

        for alt_name in self.parent_dict:
            self.parent_dict[alt_name].set_dev_status(DeviceStatus.Bootloader)
        self.status = DeviceStatus.Bootloader

        self.known_regs_structure = False
        self.max_pkt_data_size: int = 246 - 10
        self.reg_num_of_regs: int = 1
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []
        self.stay_in_bootloader = True
        self.in_bootloader = False
        return 0

    async def run_app(self, my_addr=XC2Addr.MASTER):
        """
        Send system reset request and stays in bootloader
        :param my_addr:  Address of master device (Your PC)
        :return data[0]: System status
        """
        try:
            for alt_name in self.parent_dict:
                await self.parent_dict[alt_name].run_app(my_addr=my_addr)
        except Exception as e:
            self.lower_ttl()
            raise e
        self.known_regs_structure = False
        self.max_pkt_data_size: int = 246 - 10
        self.reg_num_of_regs: int = 1
        self.reg_num_of_bytes: int = 0
        self.regs = []
        self.reg_struct_list: list[dict] = [{}]
        self.reg_parse_type_list: list = []
        self.stay_in_bootloader = False
        self.in_bootloader = False
        return 0

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

        self.addr = new_addr
        self.reset_ttl()
        self.set_last_contact()
        # TODO: proper resonse
        return b""

    async def read_serial_number(self, my_addr=XC2Addr.MASTER) -> tuple[str, str]:
        """
        Return device serial number and device type
        :param my_addr: Address of master device (Your PC)
        :return: tuple of device_type and device_ serial
        :rtype tuple:
        """
        ret_dev_type = ""
        ret_dev_serial = ""
        try:
            for alt_name in self.parent_dict:
                device_type, device_serial = await self.parent_dict[alt_name].read_serial_number(my_addr=my_addr)
                ret_dev_type += f"{device_type}, "
                ret_dev_serial += f"{device_serial}, "
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return ret_dev_type, ret_dev_serial

    async def write_baud_rate(self, new_baud_rate: int, my_addr=XC2Addr.MASTER) -> XC2Packet | bytes:
        """
        Sets new baud rate for the device
        :param new_baud_rate: New baud rate
        :param my_addr: Address of master device (Your PC)
        :return: System response
        """
        raise NotImplementedError("Tis function is useless for Virtual device")

    async def read_feature(self, my_addr=XC2Addr.MASTER) -> list[str]:
        """c
        Gets list of ID_product, ID_vendor, ID_version, ID_custom1, ID_custom2,
        save them into member vars and returns them as list
        :param my_addr: Address of your PC
        :return: list of ID_product, ID_vendor, ID_version, ID_custom1, ID_custom2
        :rtype list:
        """
        return_list = []
        try:
            for alt_name in self.parent_dict:
                data = await self.parent_dict[alt_name].read_feature(my_addr=my_addr)
                return_list.append(data)
            transposed_list = [[return_list[j][i] for j in range(len(return_list))] for i in range(len(return_list[0]))]
            string_transposed_list = [", ".join(map(str, row)) for row in transposed_list]

        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()
        return string_transposed_list

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
                raise UnknownDevRegStruct("Read device structure firsst")
            if stop > self.reg_num_of_regs - 1:
                raise ValueError("maximum index exceeded")
            if start < 0:
                raise ValueError("start must be positive value")
            if stop < start:
                raise ValueError("start > stop")

            virtual_index = start
            if self.copy_parent is not None:
                if start < self.copy_parent_num_of_regs - 1:
                    c_parent_start = start
                    c_parent_stop = stop if stop < self.copy_parent_num_of_regs - 1 else self.copy_parent_num_of_regs - 1
                    await self.parent_dict[self.copy_parent].read_regs_range(
                        start=c_parent_start,
                        stop=c_parent_stop,
                        initial_read=initial_read,
                    )
                    c_parent_data = self.parent_dict[self.copy_parent].get_regs_range(c_parent_start, c_parent_stop)

                    for index in range(c_parent_start, c_parent_stop + 1):
                        value = c_parent_data[index]
                        self.regs[virtual_index] = value
                        virtual_index += 1

            for virtual_reg_name in self.reg_name_list[start - self.copy_parent_num_of_regs : stop - self.copy_parent_num_of_regs]:
                dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
                reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
                arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
                arr_range = self.virtual_reg_dict[virtual_reg_name].get("arr_range")
                device = self.parent_dict[dev_name]
                data = await device.read_and_get_reg_by_name(reg_name)

                if arr_index is not None:
                    value = data[arr_index]
                elif arr_range is not None:
                    start = int(arr_range[: arr_range.index("-")])
                    stop = int(arr_range[arr_range.index("-") + 1 :])
                    value = data[start : stop + 1]
                else:
                    value = data
                self.regs[virtual_index] = value
                virtual_index += 1
        except ValueError as e:
            raise e
        except UnknownDevRegStruct as e:
            raise e
        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

    async def read_reg_range(self, index: int, start_stop_arr, my_addr=XC2Addr.MASTER, initial_read: bool = False):
        raise NotImplementedError("Tis function is useless for Virtual device")

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
        except UnknownDevRegStruct:
            pass
        except Exception as e:
            self.lower_ttl()
            raise e
        return ret

    def parse_regs_data(self, reg_data, start: int, stop: int, initial_read=False):
        """
        Extract data from input raw string from device
        :param reg_data:
        :param start: Index of first register
        :param stop: Index of last register
        """
        raise NotImplementedError("Tis function is useless for Virtual device")

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
        if index < self.copy_parent_num_of_regs - 1:
            await self.parent_dict[self.copy_parent].write_reg(data, index, array_index, my_addr, req_response)
        else:
            virtual_reg_name = self.reg_name_list[index - self.copy_parent_num_of_regs]
            dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
            reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
            arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
            device = self.parent_dict[dev_name]

            if arr_index is None:
                arr_index = 0

            await device.write_reg_by_name(data=data, name=reg_name, array_index=arr_index, my_addr=my_addr)
        return data

    async def write_reg_str(
        self,
        data_str,
        index,
        array_index=0,
        my_addr=XC2Addr.MASTER,
        req_response=True,
    ):
        data = self.parse_data_str(data_str, index)
        if data is not None:
            await self.write_reg(data, index, array_index, my_addr, req_response)

    def parse_data_str(self, data_str, index):
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

    def parse_list(self, value_str, value_type):
        if value_str[0] != "[" or value_str[-1] != "]":
            return
        else:
            value_list = [value_type(x) for x in value_str.replace("[", "").replace("]", "").split(",")]
            return value_list

    async def write_all_regs_default(self, all_registry=True, my_addr=XC2Addr.MASTER):
        if self.copy_parent is not None:
            await self.parent_dict[self.copy_parent].write_all_regs_default(all_registry, my_addr)

        for virtual_reg_name in self.reg_name_list:
            dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
            reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
            arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
            device = self.parent_dict[dev_name]
            default = await device.get_reg_default_value_by_name(reg_name)
            if arr_index is None:
                arr_index = 0
            await device.write_reg_by_name(data=default, name=reg_name, array_index=arr_index, my_addr=my_addr)

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
        for index in range(len(self.reg_struct_list)):
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
        if name in self.reg_name_list:
            virtual_reg_name = name
            dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
            reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
            arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
            arr_range = self.virtual_reg_dict[virtual_reg_name].get("arr_range")
            device = self.parent_dict[dev_name]
            data = await device.read_and_get_reg_by_name(reg_name)
            reg_index = self.reg_name_to_index(virtual_reg_name)

            if arr_index is not None:
                value = data[arr_index]

            elif arr_range is not None:
                start = int(arr_range[: arr_range.index("-")])
                stop = int(arr_range[arr_range.index("-") + 1 :])
                value = data[start : stop + 1]

            else:
                value = data
        else:
            ret = await self.parent_dict[self.copy_parent].read_reg_by_name(name)
            if ret:
                value = self.parent_dict[self.copy_parent].get_reg_by_name(name)
                reg_index = self.reg_name_to_index(name)
            else:
                return

        self.regs[reg_index] = value
        if value is not None:
            return True
        return False

    def reg_name_to_index(self, name: str) -> int | bool:
        """Convert register name to index

        Args:
            name (str): register name

        Returns:
            int | bool: index of register, False if not found
        """
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(len(self.reg_struct_list)):
            if self.reg_struct_list[index]["name"] == name:
                return index
        return False

    async def get_reg_structure(self, index, my_addr=XC2Addr.MASTER):
        """
        Get reg info of one register
        !!! Don't use it !!!
        !!! Use get_regs_info_structure() instead !!

        :param index: Index of register
        :param my_addr: Address of master device (Your PC)
        """
        raise NotImplementedError()

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
        try:
            virtual_reg_name = self.reg_name_list[index - self.copy_parent_num_of_regs]
            dev_name = self.virtual_reg_dict[virtual_reg_name]["parent_name"]
            reg_name = self.virtual_reg_dict[virtual_reg_name]["reg_name"]
            arr_index = self.virtual_reg_dict[virtual_reg_name].get("arr_index")
            arr_range = self.virtual_reg_dict[virtual_reg_name].get("arr_range")
            device = self.parent_dict[dev_name]
            value = device.get_reg_default_value_by_name(reg_name)
            if arr_index is not None:
                self.reg_struct_list[index]["default"] = value[arr_index]

            elif arr_range is not None:
                start = int(arr_range[: arr_range.index("-")])
                stop = int(arr_range[arr_range.index("-") + 1 :])
                self.reg_struct_list[index]["default"] = value[start : stop + 1]

            else:
                self.reg_struct_list[index]["default"] = value

        except Exception as e:
            self.lower_ttl()
            raise e
        self.reset_ttl()
        self.set_last_contact()

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
            if self.reg_name_list[reg_index] == reg_name:
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
            await self.write_reg(value, reg_index)
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
            await self.write_reg_by_name(value, reg_name)
        except Exception as e:
            raise e

    def split_reg(self, index):
        raise NotImplementedError

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
        if not self.known_regs_structure:
            raise UnknownDevRegStruct("Read device regs structure first.")
        for index in range(self.reg_num_of_regs):
            if self.reg_struct_list[index]["name"] == name:
                try:
                    await self.write_reg(data, index, array_index, my_addr, req_response)
                except Exception as e:
                    raise e
                return 0
        raise ValueError("No such register")

    async def restore_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        raise NotImplementedError("Virtual device regs cannot be restored")

    async def store_regs(self, my_addr=XC2Addr.MASTER) -> bytes:
        raise NotImplementedError("Virtual device regs cannot be stored")

    async def read_and_get_app_status(self):
        raise NotImplementedError("This XC2Device does not have app status")

    async def power_enable(self):
        raise NotImplementedError("This XC2Device does not have power_enable")

    def get_parent_dev_dict(self):
        return self.parent_dict
