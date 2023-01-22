import pytest
from attr import evolve
import datetime as dt
from bsbgateway.bsb.model import BsbType, BsbDatatype, I18nstr, ScheduleEntry
from bsbgateway.bsb.payload_decode import decode, DecodeError

KW = {"unit": I18nstr(), "name": None}

int8 = BsbType(datatype=BsbDatatype.Vals, payload_length=1, enable_byte=1, **KW)
uint8 = evolve(int8, unsigned=True)
int16 = evolve(int8, payload_length=2)
uint16 = evolve(int16, unsigned=True)
int32 = evolve(int8, payload_length=4)
int40 = evolve(int8, payload_length=5)
int16_10 = evolve(int16, factor=10)

bits = BsbType(datatype=BsbDatatype.Bits, payload_length=1, enable_byte=1, **KW)
enum = evolve(bits, datatype=BsbDatatype.Enum)

year = BsbType(unit=I18nstr(), name="YEAR", datatype=BsbDatatype.Vals, payload_length=8, enable_byte=1)
dttm = BsbType(datatype=BsbDatatype.Datetime, payload_length=8, enable_byte=1, **KW)
ddmm = evolve(dttm, datatype=BsbDatatype.DayMonth)
ddmm_v = evolve(ddmm, name="VACATIONPROG")
thms = evolve(dttm, datatype=BsbDatatype.Time)

hhmm = evolve(int16, datatype=BsbDatatype.HourMinutes)

str5 = BsbType(datatype=BsbDatatype.String, payload_length=5, enable_byte=1, **KW)
str22 = evolve(str5, payload_length=22)

tmpr = BsbType(datatype=BsbDatatype.TimeProgram, payload_length=11, enable_byte=8, **KW)

# 1985-10-26 (Sat) 01:21:01
dtval = '00 550A1A 06 011501' # flag byte to be appended

def SE(h1, m1, h2, m2):
    return ScheduleEntry(
        on=dt.time(h1, m1),
        off=dt.time(h2, m2),
    )

@pytest.mark.parametrize(
    "data, bsb_type, expect",
    [
        ('000A', int8, 10),
        ('00ff', int8, -1),
        ('00ff', uint8, 255),
        ('000102', int16, 258),
        ('00ffff', int16, -1),
        ('00ffff', uint16, 65535),
        ('000104', int16_10, 26.0),
        ('00 00010000', int32, 65536),
        ('00 0001', int32, DecodeError),
        ('00 0001000000', int40, AssertionError), # type properties are asserted, payload_length=5 is forbidden.
        ('010A', int8, None),
        ('020A', int8, None),
        ('050A', int8, None),
        ('060A', int8, 10),
        ('00FE', bits, 254),
        ('00FE', enum, 254),
        ('000102', year, DecodeError),
        (dtval + '0F', year, 1985),
        (dtval + '21', year, DecodeError), #wrong flag (last byte)
        (dtval + '00', dttm, dt.datetime(1985, 10, 26, 1, 21, 1)),
        (dtval + '01', dttm, DecodeError),
        (dtval + '16', ddmm, dt.date(1900, 10, 26)),
        (dtval + '17', ddmm, DecodeError),
        (dtval + '17', ddmm_v, dt.date(1900, 10, 26)),
        (dtval + '16', ddmm_v, DecodeError),
        (dtval + '1d', thms, dt.time(1, 21, 1)),
        (dtval + '1e', thms, DecodeError),
        ('00 0115', hhmm, dt.time(1, 21, 0)),
        # per our logic, actual payload length is 6 (since flag byte is discounted)
        ('65 66 67 00 00 00', str5, "efg"),
        ('65 66 67 00 00', str5, DecodeError),
        # if type length is 22, expect actual 22 bytes
        ('65 66 67' + '00'*18, str22, DecodeError),
        ('65 66 67' + '00'*19, str22, "efg"),
        ('65 66 67' + '00'*20, str22, DecodeError),
        ('8000 0000 8000 0000 8000 0000', tmpr, []),
        ('0102 0304 8000 0000 8000 0000', tmpr, [SE(1,2,3,4)]),
        ('0102 0304 0203 0405 8000 0000', tmpr, [SE(1,2,3,4), SE(2, 3, 4, 5)]),
        ('0102 0304 8000 8000 0203 0405', tmpr, [SE(1,2,3,4), SE(2, 3, 4, 5)]),
        ('0102 0304 0100 0300 0203 0405', tmpr, [SE(1,2,3,4), SE(1,0,3,0), SE(2, 3, 4, 5)]),

    ]
)
def test_decode(data, bsb_type, expect):
    data = bytes.fromhex(data.replace(" ", ""))
    if isinstance(expect, type):
        with pytest.raises(expect):
            _ = decode(data, bsb_type)
    else:
        val = decode(data, bsb_type)
        assert val == expect
        assert type(val) is type(expect)
