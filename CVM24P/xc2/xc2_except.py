class IncompletePacket(Exception):
    pass


class BadCrc(Exception):
    pass


class UnimplementedCommand(Exception):
    pass


class UnexpectedAnswerError(Exception):
    pass


class GeneralError(Exception):
    pass


class XC2TimeoutError(Exception):
    pass


class XC2ConnectionClosed(Exception):
    pass


class XC2DeviceNotResponding(Exception):
    pass


class UnknownDevRegStruct(Exception):
    pass
