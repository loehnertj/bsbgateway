import struct
import datetime as dt
from .model import BsbType, BsbDatatype,ScheduleEntry
from .errors import DecodeError



def decode(data:bytes, type:BsbType) -> object:
    expect_len = min(type.payload_length+1, 22)
    if len(data) != expect_len:
        raise DecodeError("Payload has wrong length. Expected %d bytes, got %d" % (type.payload_length+1, len(data)))
    if type.datatype not in (BsbDatatype.TimeProgram, BsbDatatype.String):
        # Flagged type
        flag = data[0]
        # Null value?
        if flag != 0 and flag != 6:
            return None
        data = data[1:]
    if type.name in _CUSTOM_DECODERS:
        decoder = _CUSTOM_DECODERS[type.name]
    else:
        if type.datatype not in _DECODERS:
            return data
        decoder = _DECODERS[type.datatype]
    return decoder(data, type)

def decode_vals(data: bytes, type: BsbType):
    """Decodes numeric value.
    Returns int if type.factor=1, float if otherwise.
    """
    assert type.payload_length in [1, 2, 4]
    code = {1:"b", 2:"h", 4:"i"}[type.payload_length]
    if type.unsigned or type.datatype != BsbDatatype.Vals:
        code = code.upper()
    intval, = struct.unpack(">"+code, data)
    if type.factor == 1:
        return intval
    else:
        return float(intval) / type.factor
    

def decode_hourminute(data:bytes, type:BsbType):
    assert type.payload_length == 2
    assert len(data) == 2
    hour, minute = struct.unpack("2b", data)
    return dt.time(hour, minute, 0)


def decode_dt(data: bytes, type:BsbType):
    year, month, day, dow, hour, minute, second, flag = (
        struct.unpack("8b", data)
    )
    year = year + 1900

    def expect_flag(t):
        if flag != t:
            raise DecodeError("Datetime field: Expected subtype %d, got %d" % (t, flag))
    if type.name == "YEAR":
        expect_flag(0x0f)
        return year
    elif type.name == "VACATIONPROG":
        expect_flag(0x17)
        # FIXME: nur wochentag wichtig?
        return dt.date(1900, month, day)
    elif type.datatype == BsbDatatype.Datetime:
        expect_flag(0x0)
        return dt.datetime(year, month, day, hour, minute, second)
    elif type.datatype == BsbDatatype.DayMonth:
        expect_flag(0x16)
        return dt.date(1900, month, day)
    elif type.datatype == BsbDatatype.Time:
        expect_flag(0x1d)
        return dt.time(hour, minute, second)
    else:
        raise DecodeError("Could not decode datetime field")

def decode_string(data:bytes, type:BsbType) -> str:
    if b'\0' in data:
        data = data[:data.index(b'\0')]
    return data.decode("latin-1")

def decode_enum(data:bytes, type:BsbType) -> int:
    """Returns the numeric value. Cannot convert to EnumValue without knowing
    the BsbCommand."""
    assert type.payload_length == 1
    assert len(data) == 1
    val, = struct.unpack("B", data)
    return val

def decode_timeprogram(data:bytes, type:BsbType):
    """Timeprogram is returned as list of up to three tuples (On, Off)"""
    assert len(data) == 12
    result = []
    for ofs in [0, 4, 8]:
        if data[ofs] & 0x80 != 0:
            # disabled
            continue
        h1, m1, h2, m2 = struct.unpack("4B", data[ofs:ofs+4])
        result.append(ScheduleEntry(
            on=dt.time(h1, m1, 0),
            off=dt.time(h2, m2, 0)
        ))
    return result


_DECODERS = {
    BsbDatatype.Vals: decode_vals,
    BsbDatatype.Bits: decode_vals,
    BsbDatatype.Enum: decode_enum,
    # PPS only. Not supported.
    #BsbDatatype.Date: decode_date,
    BsbDatatype.Datetime: decode_dt,
    BsbDatatype.DayMonth: decode_dt,
    BsbDatatype.HourMinutes: decode_hourminute,
    BsbDatatype.Time: decode_dt,
    BsbDatatype.TimeProgram: decode_timeprogram,
    BsbDatatype.String: decode_string,
}

# Exceptions :-)
_CUSTOM_DECODERS = {
    "YEAR": decode_dt,
    # 702 Praesenztaste, 22 Bytes (?) Not supported
    #"CUSTOM_ENUM": decode_custom_enum
}