from .packets import XC2Packet
from .consts import XC2PacketType, XC2Commands, XC2Flags, LogPktType

import csv
from datetime import datetime

FLAG_ADDR = "ADDR"
FLAG_TIMESTAMP = "DATE_TIME"
FLAG_CMP = "CMP"
FLAG_HMN = "HMN"


class CommLogBase:
    """Common class for all XC2 communication loggers"""

    def __init__(self):
        pass

    def log_pkt(self, pkt, log_type: LogPktType):
        """Logs a packet. This method must be implemented by the child class.

        :param pkt: Packet to be logged
        :type pkt: XC2Packet or any other packet class
        :param log_type: Type of packet to be logged based on :any:`LogPktType`
        :type log_type: LogPktType
        :raises NotImplementedError: Raised when the method is not implemented by the child class
        """
        raise NotImplementedError

    def parse_xc2_to_human_readable(self, xc2_pkt: XC2Packet) -> dict:
        """Parses a XC2Packet to a human readable dictionary. Converts the packet type, command and flags to their
        respective names.

        :param xc2_pkt: Packet to be parsed
        :type xc2_pkt: XC2Packet
        :return: Dictionary with the human readable packet
        :rtype: dict
        """
        # TODO: do something where there is not match
        xc2_hmn: dict = {}

        for pkt_type in XC2PacketType:
            if xc2_pkt.pktype == pkt_type.value:
                xc2_hmn["pkt_type"] = pkt_type.name

        for command in XC2Commands:
            if xc2_pkt.cmd == command.value:
                xc2_hmn["cmd"] = command.name

        xc2_hmn["data"] = xc2_pkt.data
        xc2_hmn["flags"] = ""

        for flag in XC2Flags:
            if xc2_pkt.flags & flag.value:
                xc2_hmn["flags"] = xc2_hmn["flags"] + flag.name
        return xc2_hmn


class PySideLogger(CommLogBase):
    """Logger class for PySide GUI. This class is responsible for logging the packets on the GUI console and in a file
    if the user chooses to do so.
    """

    def __init__(
        self,
        log_console: bool,
        log_file: bool,
        write_on_console_sig=None,
        write_file_sig=None,
    ):
        """
        In order to log packets into console or file, the user must provide the signals to do so. The signals must be
        of the type :any:`PySide6.QtCore.Signal` and must have the following signature: ``signal(str, str)``. The first
        argument is the text to be logged and the second argument is the flag to be used.

        :param log_console: Whether to log on the console or not
        :type log_console: bool
        :param log_file: Whether to log on a file or not
        :type log_file: bool
        :param write_on_console_sig: Signal to write on the console, defaults to None
        :type write_on_console_sig: signal(str, str), optional
        :param write_file_sig: Signal to write on a file, defaults to None
        :type write_file_sig: signal(str, str), optional
        """
        super().__init__()
        self.log_console = log_console and (write_on_console_sig is not None)
        self.log_file = log_file and (write_file_sig is not None)
        self.write_on_console_sig = write_on_console_sig
        self.write_file_sig = write_file_sig

    def log_pkt(self, pkt: XC2Packet, log_type: int, background_msg=False):
        """Logs a packet. The packet is logged on the console and/or on a file if the user chooses to do so.
        The logged packet is classified based on the type of packet. The packet type can be one of the following:
        :any:`LogPktType.INPUT_PKT`, :any:`LogPktType.OUTPUT_PKT` or :any:`LogPktType.EVENT_PKT`.

        :param pkt: Packet to be logged
        :type pkt: XC2Packet
        :param log_type: Type of packet to be logged based on :any:`LogPktType`
        :type log_type: LogPktType | int
        :param background_msg: Whether the packet is a background message or not, defaults to False
        :type background_msg: bool, optional
        """
        if self.log_file:
            self.file_log_pkt(pkt)
        if self.log_console:
            match log_type:
                case LogPktType.INPUT_PKT:
                    self.console_log_in_pkt(xc2_pkt=pkt, background_msg=background_msg)
                case LogPktType.OUTPUT_PKT:
                    self.console_log_out_pkt(xc2_pkt=pkt, background_msg=background_msg)
                case LogPktType.EVENT_PKT:
                    self.console_log_event_pkt(xc2_pkt=pkt)
                case _:
                    # TODO: create custom event error
                    pass

    def gen_console_output_direct(self, text: str, flag: str):
        """Generates a raw console output. This method is used to directly emit a signal for
        the console widget to write a text into it without any modifications to the text.

        :param text: Text to be logged
        :type text: str
        :param flag: Flag to be used
        :type flag: str
        """
        self.write_on_console_sig.emit(text, flag)

    def gen_console_output(self, text: str, **kwargs):
        """Generates a formatted console output. Additional style can be added to the text by passing
        appropriate keyword arguments. The keyword arguments must be the same as the CSS style
        properties.

        :param text: Text to be logged
        :type text: str
        """
        form_str: str = "<p"
        if any(kwargs):
            form_str += ' style="'
        for key in kwargs:
            new_str = f'{key}: {kwargs[key]};" '
            form_str += new_str
        new_str = f">{text}</p>"
        form_str += new_str
        self.write_on_console_sig.emit(form_str, "SYSTEM")

    def console_log_in_pkt(self, xc2_pkt: XC2Packet, background_msg=False):
        """Logs an incoming packet on the console. The packet is logged with a blue color.

        :param xc2_pkt: Packet to be logged
        :type xc2_pkt: XC2Packet
        :param background_msg: Whether the packet is a background message or not, defaults to False
        :type background_msg: bool, optional
        """
        flag_addr: str = FLAG_ADDR if not background_msg else "BACK_" + FLAG_ADDR
        flag_cmp: str = FLAG_CMP if not background_msg else "BACK_" + FLAG_CMP
        flag_hmn: str = FLAG_HMN if not background_msg else "BACK_" + FLAG_HMN
        flag_timestamp: str = FLAG_TIMESTAMP if not background_msg else "BACK_" + FLAG_TIMESTAMP

        now: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")

        self.gen_console_output_direct(
            f'<div style= "color: blue; font: bold;">{hex(xc2_pkt.src)}->{hex(xc2_pkt.dst)} </div>',
            flag=flag_addr,
        )

        self.gen_console_output_direct(
            f'<div style= "color: blue; font: bold;"> {now} </div>',
            flag=flag_timestamp,
        )

        self.gen_console_output_direct(
            f'<div style= "color: blue;">PKT TYPE: {hex(xc2_pkt.pktype)}, CMD:'
            f" {hex(xc2_pkt.cmd)}, DATA: {xc2_pkt.data}, FLAGS: "
            f" {hex(xc2_pkt.flags)} [{xc2_pkt.length} bytes]</div>",
            flag=flag_cmp,
        )
        xc2_hmn_dict: dict = self.parse_xc2_to_human_readable(xc2_pkt)

        self.gen_console_output_direct(
            f'<div style= "color: blue;">PKT TYPE: {xc2_hmn_dict["pkt_type"]},'
            f' CMD: {xc2_hmn_dict["cmd"]}, DATA: {xc2_hmn_dict["data"]}, FLAGS: '
            f' {xc2_hmn_dict["flags"]} [{xc2_pkt.length} bytes]</div>',
            flag=flag_hmn,
        )

    def console_log_out_pkt(self, xc2_pkt: XC2Packet, background_msg=False):
        """Logs an outgoing packet on the console. The packet is logged with a green color.

        :param xc2_pkt: Packet to be logged
        :type xc2_pkt: XC2Packet
        :param background_msg: Whether the packet is a background message or not, defaults to False
        :type background_msg: bool, optional
        """
        flag_addr = FLAG_ADDR if not background_msg else "BACK_" + FLAG_ADDR
        flag_cmp = FLAG_CMP if not background_msg else "BACK_" + FLAG_CMP
        flag_hmn = FLAG_HMN if not background_msg else "BACK_" + FLAG_HMN
        flag_timestamp = FLAG_TIMESTAMP if not background_msg else "BACK_" + FLAG_TIMESTAMP

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")

        self.gen_console_output_direct(
            f'<div style= "color: green; font: bold;">{hex(xc2_pkt.src)}->{hex(xc2_pkt.dst)} </div>',
            flag=flag_addr,
        )

        self.gen_console_output_direct(
            f'<div style= "color: green; font: bold;"> {now} </div>',
            flag=flag_timestamp,
        )

        self.gen_console_output_direct(
            f'<div style= "color: green;">PKT TYPE: {hex(xc2_pkt.pktype)}, CMD:'
            f" {hex(xc2_pkt.cmd)}, DATA: {xc2_pkt.data}, FLAGS: "
            f" {hex(xc2_pkt.flags)} [{xc2_pkt.length} bytes]</div>",
            flag=flag_cmp,
        )
        xc2_hmn_dict = self.parse_xc2_to_human_readable(xc2_pkt)

        self.gen_console_output_direct(
            f'<div style= "color: green;">PKT TYPE: {xc2_hmn_dict["pkt_type"]},'
            f' CMD: {xc2_hmn_dict["cmd"]}, DATA: {xc2_hmn_dict["data"]}, FLAGS: '
            f' {xc2_hmn_dict["flags"]} [{xc2_pkt.length} bytes]</div>',
            flag=flag_hmn,
        )

    def console_log_event_pkt(self, xc2_pkt: XC2Packet):
        """Logs an event packet on the console. The packet is logged with an orange color.

        :param xc2_pkt: Packet to be logged
        :type xc2_pkt: XC2Packet
        """
        self.gen_console_output_direct(
            f'<div style= "color: orange; font: bold;">{hex(xc2_pkt.src)}->{hex(xc2_pkt.dst)} </div>',
            flag="ADDR",
        )

        self.gen_console_output_direct(
            f'<div style= "color: orange;">PKT TYPE: {hex(xc2_pkt.pktype)}, CMD:'
            f" {hex(xc2_pkt.cmd)}, DATA: {xc2_pkt.data}, FLAGS: "
            f" {hex(xc2_pkt.flags)} [{xc2_pkt.length} bytes]</div>",
            flag="CMP",
        )
        xc2_hmn_dict: dict = self.parse_xc2_to_human_readable(xc2_pkt)

        self.gen_console_output_direct(
            f'<div style= "color: orange;">PKT TYPE: {xc2_hmn_dict["pkt_type"]},'
            f' CMD: {xc2_hmn_dict["cmd"]}, DATA: {xc2_hmn_dict["data"]}, FLAGS: '
            f' {xc2_hmn_dict["flags"]} [{xc2_pkt.length} bytes]</div>',
            flag="HMN",
        )

    def file_log_pkt(self, xc2_pkt: XC2Packet):
        """Logs a packet on a file. The packet is sent with a signal to be written in a file.
        The format of the logged packet text is the same as the one used on the console.

        :param xc2_pkt: Packet to be logged
        :type xc2_pkt: XC2Packet
        """
        now: str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.write_file_sig.emit(f"{hex(xc2_pkt.src)}->{hex(xc2_pkt.dst)}, ({now})", "ADDR")
        self.write_file_sig.emit(
            f"PKT TYPE: {hex(xc2_pkt.pktype)}, CMD: {hex(xc2_pkt.cmd)}, DATA: {xc2_pkt.data}, FLAGS:  {hex(xc2_pkt.flags)} [{xc2_pkt.length} bytes]",
            "CMP",
        )
        xc2_hmn_dict: dict = self.parse_xc2_to_human_readable(xc2_pkt)

        self.write_file_sig.emit(
            f'PKT TYPE: {xc2_hmn_dict["pkt_type"]}, CMD: {xc2_hmn_dict["cmd"]},'
            f' DATA: {xc2_hmn_dict["data"]}, FLAGS: '
            f' {xc2_hmn_dict["flags"]} [{xc2_pkt.length} bytes]',
            "HMN",
        )


class CommFileLog:
    """Class for writing logs in a file."""

    def __init__(self, file_path: str):
        """
        :param file_path: Path to the file to be written to
        :type file_path: str
        """
        self.file_path: str = file_path
        self.writer: csv.writer = None
        self.data_file = None

    def open_file_log(self):
        """Opens the file to be written to."""
        self.data_file = open(self.file_path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.data_file)

    def update_file_log(self, text: str):
        """Writes a text in the file.

        :param text: Text row to be written
        :type text: str
        """
        if self.data_file is not None and self.writer is not None:
            self.writer.writerow([text])

    def save_file_log(self):
        """Saves the file in which the logs are being written to."""
        if self.data_file is not None:
            self.data_file.close()
            self.data_file = None
            self.writer = None
