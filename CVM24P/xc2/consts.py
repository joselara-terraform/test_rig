from enum import IntEnum

MAX_BAUD_RATE = 3000000
MAX_XC2_ADDRESS = 4096
NUMBER_OF_REPETITIONS = 4
TIMEOUT_RESPONSE = 400


class XC2PacketType(IntEnum):
    """Specifies the type of packet."""

    COMMAND = 0x80
    ACK = 0xC0
    NAK = 0xE0
    EVENT = 0x40
    CRITICAL_ERROR = 0x60  # criticall error event


class XCTPacketType(IntEnum):
    SERVER = 0x00
    DEVICE = 0x01
    ANSWER = 0x03

    def __str__(self):
        return self.name


class XC2Flags(IntEnum):
    """Specifies the possible flags for the packet."""

    MULTICAST = 0x80
    SUPPRESS_ANSWER = 0x40
    REPETITION_FLAG = 0x20
    RESERVED = 0x10
    NO_FLAG = 0x00
    # NO_FLAG = 0x00


class XC2Addr(IntEnum):
    """Reserved addresses and address conventions"""

    BROADCAST = 0x000
    DEFAULT = 0xFFF
    MASTER = 0x001


class XCTFeedbackChannel(IntEnum):
    Current = 0x0
    Vhpt = 0x01
    Vout = 0x02
    Vsense = 0x03
    Vref = 0x04

    def __str__(self):
        return self.name


class XCTVChannel(IntEnum):
    Vout = 0x00
    Vsense = 0x01
    Vref = 0x02

    def __str__(self):
        return self.name


class XCTRecordChannel(IntEnum):
    Vout = 0x01
    Vsense = 0x02
    Vref = 0x04
    I = 0x08

    def __str__(self):
        return self.name


class XCTCommands(IntEnum):
    GET = 0x00
    SET = 0x01
    ECHO = 0x02
    REST = 0x03
    PLAIN_CMD = 0x04

    OK = 200
    ERROR = 0xFF

    def __str__(self):
        return self.name


class XC2Commands(IntEnum):
    """Commands for XC2 comm"""

    CMD_POLL = 0x00
    CMD_ECHO = 0x01  # Replies with bootloader/application id
    CMD_GET_STATUS = 0x02  # Read device-specific status
    CMD_SYS = 0x03
    CMD_GET_FEATURE = 0x05  # Read vendor/product IDs, firmware version and custom IDs strings
    # <ID_product> <ID_vendor> <ID_version> <ID_custom1> <ID_custom2>
    CMD_FIND = 0x06  # Searches for devices within specified address range – for broadcast
    CMD_BLCMD = 0x08
    CMD_STAY_IN_BOOTLOADER = 0x09
    # Registry
    CMD_Registry_ReadRaw = 0x10
    CMD_Registry_Read = 0x11
    CMD_Registry_ReadByName = 0x12
    CMD_Registry_GetInfo = 0x13
    CMD_Registry_WriteRaw = 0x14
    CMD_Registry_Write = 0x15
    CMD_Registry_WriteByName = 0x16
    CMD_Registry_Action = 0x17

    CMD_Xadda_AcqBuffer_Read = 0x91
    CMD_CVM_APPSTATUS = 0xA0
    CMD_APPSTATUS = 0xA0

    # APP variables
    CLEAR = 0
    SET = 1
    TOGGLE = 2
    READ = 0
    RESET = 1
    DISABLE_BY_MASK = 2

    # XAM specific
    CMD_XAM_APPREADWRITE = 0xA1
    CMD_XAM_APPREADWRITE_ALL = 0xA2
    CMD_XAM_APPFUSES = 0xB0

    # DIO specific
    CMD_DIO_APPREADWRITE = 0xA1
    CMD_DIO_APPREADWRITE_ALL = 0xA2
    CMD_DIO_APPFUSES = 0xB0

    # MIS specific
    CMD_MIS_C2 = 0xC2
    CMD_MIS_BUFF = 0x91


class XC2SysSubcommands(IntEnum):
    """Subcommands inserted into data after command"""

    ECHO_BOOT_LOADER = 0x01
    ECHO_APPLICATION = 0x02
    SYS_RESET = 0x04
    SYS_BOOTLOADER = 0x06
    SYS_RUNAPPL = 0x07
    SYS_SETADDR = 0x10
    SYS_GETSERIAL = 0x13
    SYS_SETBAUD = 0x14
    SYS_SETBAUD_DIRECT = 0x15
    SYS_RESTORE_REGS = 0x20
    SYS_STORE_REGS = 0x21
    BL_GETBUFFSIZE = 0x01
    BL_WRITEBUF = 0x02
    BL_PROGFLASH = 0x05
    BL_APPLCRC = 0x08


class XC2RegGetInfoSubcommands(IntEnum):
    """Subcommands for registry get info command"""

    RegistryInfo_Size = 0x00
    RegistryInfo_Structure = 0x01
    RegistryInfo_FindByName = 0x02
    RegistryInfo_DefaultValue = 0x03
    RegistryInfo_EnumsCount = 0x04
    RegistryInfo_EnumLen = 0x05
    RegistryInfo_EnumItems = 0x06


class XC2RegActionSubcommands(IntEnum):
    """Subcommands for registry action command"""

    RegistryAction_Backup = 0x01
    RegistryAction_Restore = 0x02
    RegistryAction_Log = 0x03
    RegistryAction_SetDefaults = 0x04
    RegistryAction_StoreToEeprom = 0x05


class XC2AcqRunningFlags(IntEnum):
    """Subcommands for xadda acq buffer read command"""

    ACQ_FLAG_RUNNING = 0x01
    ACQ_FLAG_FREEZE = 0x80
    ACQ_FLAG_FREEZE_LAST = 0x40


class XC2AnswerCmds(IntEnum):
    """codes returned in NAK type packets"""

    ANS_ACK = 0x01  # Acknowledge
    ANS_NAK = 0x02  # Generic error
    ANS_UNKNOWNCMD = 0x03  # Unknown command
    ANS_BADPRM = 0x04  # Bad parameter value
    ANS_BADLEN = 0x05  # Bad data length
    ANS_BADSECCRC = 0x06  # Bad secondary CRC
    ANS_READONLY = 0x07  # Registry or parameter is read-only
    ANS_WRITEONLY = 0x08  # Registry or parameter is write-only
    ANS_BUSY = 0x09  # Busy
    ANS_OTHERCMDINPROGRESS = 0x0A  # Other command is in progress
    ANS_NOTAPPLICABLE = 0x0B  # Command not applicable at this moment


class XC2RegFlags(IntEnum):
    """flags returned from registry"""

    FL_MASK_TYPE = 0x07
    FL_1 = 0x01  # 1-bit variable / boolean
    FL_8 = 0x02  # 8-bit variable / byte
    FL_16 = 0x03  # 16-bit variable / word
    FL_32 = 0x04  # 32-bit variable / double word
    FL_64 = 0x05  # 64-bit variable / quad word
    FL_MASK_MOD = 0x18
    FL_U = 0x00  # unsigned int
    FL_I = 0x08  # signed int
    FL_FE = 0x10  # float/enum
    FL_CH = 0x18  # char
    FL_ARR = 0x20  # is an array
    FL_BND = 0x40  # check Min Max bounds, must be set also for enums
    FL_HEX = 0x80  # prefer printing of integer values in hex
    FL_RO = 0x100  # read-only
    FL_VAL = 0x200  # volatile


class XC2ModbusFceCode(IntEnum):
    """Modbus function codes"""

    XC2_PACKET_FCN = 0x42


class ProtocolEnum(IntEnum):
    """Specifies the type of protocol."""

    XC2 = 0x00
    Modbus = 0x01
    XCT = 0x03

    def __str__(self):
        return self.name


PROTOCOL_ENUM_DICT = {"XC2": ProtocolEnum.XC2, "MOD": ProtocolEnum.Modbus}


class LogPktType(IntEnum):
    """Specifies the type of packet for logging purposes."""

    INPUT_PKT = 0x00
    OUTPUT_PKT = 0x01
    EVENT_PKT = 0x02


class DeviceStatus(IntEnum):
    """Specifies the status of the device."""

    Expected = 0x00
    Available = 0x01
    Disconnected = 0x02
    Timeout = 0x3
    Resetting = 0x4
    Bootloader = 0x5
    Firmware = 0x6
    Unknown = 0x7

    def __str__(self):
        return self.name

    # def __str__(self):
    #     if self.value == 0x00:
    #         return "Expected"
    #     elif self.value == 0x01:
    #         return "Available"
    #     elif self.value == 0x02:
    #         return "Disconnected"
    #     elif self.value == 0x03:
    #         return "Timeout"
    #     elif self.value == 0x04:
    #         return "Resetting"
    #     elif self.value == 0x05:
    #         return "Bootloader"
    #     elif self.value == 0x06:
    #         return "Firmware"
    #     elif self.value == 0x07:
    #         return "Unknown"
    #     else:
    #         raise ValueError("No such value possible")


class BusStatus(IntEnum):
    """Specifies the status of the bus."""

    Expected = 0x00
    Available = 0x01
    Disconnected = 0x02

    def __str__(self):
        return self.name

    # def __str__(self):
    #     if self.value == 0x00:
    #         return "Expected"
    #     elif self.value == 0x01:
    #         return "Available"
    #     elif self.value == 0x02:
    #         return "Disconnected"
    #     else:
    #         raise ValueError("No such value possible")


class DeviceType(IntEnum):
    """Specifies the type of the device from list of supported Kolibrik.net devices."""

    Generic = 0x00
    Aio = 0x01
    Cvm24p = 0x02
    Cvm32a = 0x03
    Dio = 0x04
    Pmm = 0x05
    Rel = 0x06
    Xam = 0x07
    Evm8 = 0x08
    Evm8Core = 0x09
    Cvm64h = 0x10
    Hvload = 0x11
    Dctrl = 0x12
    Mis = 0x13
    Virtual = 0x42
    Virtual_Hvl = 0x43
    Virtual_Shunt = 0x44

    def __str__(self):
        if self.value == 0x00:
            return "Generic"
        elif self.value == 0x01:
            return "KlAIO"
        elif self.value == 0x02:
            return "CVM24p"
        elif self.value == 0x03:
            return "CVM32a"
        elif self.value == 0x04:
            return "KlDIO"
        elif self.value == 0x05:
            return "KlPMM"
        elif self.value == 0x06:
            return "KlREL"
        elif self.value == 0x07:
            return "KlXAM"
        elif self.value == 0x08:
            return "EVM8"
        elif self.value == 0x09:
            return "EVM8_CORE"
        elif self.value == 0x10:
            return "CVM64h"
        elif self.value == 0x11:
            return "HVLOAD"
        elif self.value == 0x12:
            return "DCTRL"
        elif self.value == 0x13:
            return "MIS"
        elif self.value == 0x42:
            return "Virtual"
        elif self.value == 0x43:
            return "Virtual_Hvl"
        elif self.value == 0x44:
            return "Virtual_Shunt"
        else:
            raise ValueError("No such value possible")

    @staticmethod
    def from_str(label: str) -> "DeviceType":
        """Converts string to DeviceType enum.

        :param label: String to be converted to DeviceType enum.
        :type label: str
        :return: DeviceType enum.
        :rtype: DeviceType
        """
        label = label.lower()
        if "aio" in label:
            return DeviceType.Aio
        elif "cvm24" in label:
            return DeviceType.Cvm24p
        elif "cvm32" in label:
            return DeviceType.Cvm32a
        elif "cvm64" in label:
            return DeviceType.Cvm64h
        elif "dio" in label:
            return DeviceType.Dio
        elif "pmm" in label:
            return DeviceType.Pmm
        elif "rel" in label:
            return DeviceType.Rel
        elif "xam" in label:
            return DeviceType.Xam
        elif "core" in label:
            return DeviceType.Evm8Core
        elif "evm8" in label:
            return DeviceType.Evm8
        elif "hvload" in label:
            return DeviceType.Hvload
        elif "dctrl" in label:
            return DeviceType.Dctrl
        elif "mis" in label:
            return DeviceType.Mis
        elif "virtual_hvl" in label:
            return DeviceType.Virtual_Hvl
        elif "virtual_sh" in label:
            return DeviceType.Virtual_Shunt
        elif "virtual" in label:
            return DeviceType.Virtual
        elif "gener" in label:
            return DeviceType.Generic
        else:
            return DeviceType.Generic


XC2RegFlagsDict = {
    XC2RegFlags.FL_1: "boolean",
    XC2RegFlags.FL_8: "byte",
    XC2RegFlags.FL_16: "word",
    XC2RegFlags.FL_32: "double word",
    XC2RegFlags.FL_64: "quad word",
    XC2RegFlags.FL_U: "unsigned int",
    XC2RegFlags.FL_I: "signed int",
    XC2RegFlags.FL_FE: "float/enum",
    XC2RegFlags.FL_CH: "char",
}

XC2RegFlagSizeDixt = {
    XC2RegFlags.FL_1: 1,
    XC2RegFlags.FL_8: 1,
    XC2RegFlags.FL_16: 2,
    XC2RegFlags.FL_32: 4,
    XC2RegFlags.FL_64: 8,
}

XC2_PARSE_TYPE_DICT = {
    XC2RegFlags.FL_U: {
        XC2RegFlags.FL_1: "B",  # BOOLEAN is formatted like unsigned int
        XC2RegFlags.FL_8: "B",
        XC2RegFlags.FL_16: "H",
        XC2RegFlags.FL_32: "L",
        XC2RegFlags.FL_64: "Q",
    },
    XC2RegFlags.FL_I: {
        XC2RegFlags.FL_1: "b",  # BOOLEAN is formatted like unsigned int
        XC2RegFlags.FL_8: "b",
        XC2RegFlags.FL_16: "h",
        XC2RegFlags.FL_32: "l",
        XC2RegFlags.FL_64: "q",
    },
    XC2RegFlags.FL_FE: {
        XC2RegFlags.FL_1: None,  # TODO: write right values
        XC2RegFlags.FL_8: None,
        XC2RegFlags.FL_16: None,
        XC2RegFlags.FL_32: "f",
        XC2RegFlags.FL_64: None,
    },
    XC2RegFlags.FL_CH: {
        XC2RegFlags.FL_1: None,  # BOOLEAN is formatted like unsigned int
        XC2RegFlags.FL_8: "c",
        XC2RegFlags.FL_16: None,
        XC2RegFlags.FL_32: None,
        XC2RegFlags.FL_64: None,
    },
}
