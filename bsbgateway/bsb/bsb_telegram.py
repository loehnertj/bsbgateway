
##############################################################################
#
#    Part of BsbGateway
#    Copyright (C) Johannes Loehnert, 2013-2015
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from crc16pure import crc16xmodem
from bsb_field import BsbField
from bsb_fields import fields_by_telegram_id

__all__ = ['DecodeError', 'BsbTelegram']

_PACKETTYPES = {
    2: 'inf',
    3: 'set',
    4: 'ack',
    6: 'get',
    7: 'ret',
}

_PACKETTYPES_R = {
    value: key for key, value in _PACKETTYPES.iteritems()
}



class DecodeError(Exception): pass


class BsbTelegram(object):
    '''src = source address (0...255)
    dst = destination address (0...255)
    packettype = telegram type
    field = 32bit field code
    data = converted payload data
    '''
    timestamp=0
    src = 0
    dst = 0
    packettype = ''
    field = None
    rawdata = []
    data = None

    def __init__(o):
        src = 0
        dst = 0
        o.packettype = ''
        o.field = None
        o.rawdata = []
        o.data = None

    @classmethod
    def deserialize(cls, data):
        '''returns a list of BsbTelegrams and unparseable data, if any.
        For unparseable data, the list entry is a tuple: (data sequence, error message)
        Order follows the input stream order.
        '''
        indata = data
        if isinstance(indata, basestring):
            indata = map(ord, indata)
        result = []

        while indata:
            try:
                t, indata = cls._parse(indata)
                result.append(t)
            except DecodeError, e:
                junk, indata = cls._skip(indata)
                result.append((''.join(map(chr, junk)), e.args[0]))
        return result

    @classmethod
    def _skip(cls, data):
        '''skip to next possible start byte (recognised by magic 0xDC byte).
        returns data splitted in (junk, gold) where junk are the skipped bytes
        and gold is the rest.
        '''
        try:
            idx = data.index(0xdc, 1)
        except ValueError:
            return data, []
        return data[:idx], data[idx:]

    @classmethod
    def _validate(cls, data):
        if data[0] != 0xdc:
            raise DecodeError("bad start marker")
        if len(data) < 4 or len(data) < data[3]:
            raise DecodeError("incomplete telegram")

        tlen = data[3]
        if tlen < 11:
            raise DecodeError("bad length: telegram cannot be shorter than 11 bytes")
        crc = crc16xmodem(data[:tlen])
        if crc!=0:
            pretty = ''.join('%0.2X '%i for i in data[:tlen])
            raise DecodeError("bad crc checksum for: " + pretty)

    @classmethod
    def _parse(cls, data):
        '''return cls instance, rest of data'''
        cls._validate(data)

        t = cls()
        t.src = data[1] ^ 0x80
        t.dst = data[2]
        dlen = data[3]
        t.packettype = _PACKETTYPES.get(data[4], 'unknown (%d)'%(data[4]))

        mult = 0x1000000
        # bei requests sind byte 5+6 getauscht
        if t.packettype in ['get', 'set']:
            data[5], data[6] = data[6], data[5]

        fieldid=0
        for d in data[5:9]:
            fieldid, mult = d*mult+fieldid, mult / 0x100

        t.field = fields_by_telegram_id.get(fieldid, BsbField(telegram_id=fieldid,disp_id=0,disp_name='Unbekannt'))
        t.rawdata = data[9:dlen-2]
        if t.rawdata:
            t.data = t.field.decode(t.rawdata)
        else:
            t.data = None

        return t, data[dlen:]

    def serialize(o, validate=True):
        '''returns ready-to-send telegram as binary string.'''
        result = [
            0xdc,
            o.src ^ 0x80,
            o.dst,
            0, # length to be set
            _PACKETTYPES_R[o.packettype],
        ]
        id = o.field.telegram_id
        id = [(id & 0xff000000) >> 24, (id & 0xff0000) >> 16, (id & 0xff00) >> 8, id & 0xff]
        if o.packettype in ['get', 'set']:
            id[1], id[0] = id[0], id[1]
        result += id

        if o.packettype in ['set', 'ret']:
            result += o.field.encode(o.data, o.packettype, validate=validate)

        # set length
        result[3] = len(result)+2

        # add crc
        crc = crc16xmodem(result)
        result.append((crc & 0xff00) >> 8)
        result.append(crc & 0xff)

        return ''.join(map(chr, result))




    def __repr__(o):
        d = o.__dict__.copy()
        d['rawdata'] = ''.join(['%0.2X '%i for i in o.rawdata])
        d['ts'] = ' @%f'%o.timestamp if o.timestamp else ''
        d['unit'] = ' '+o.field.unit.encode('utf8') if o.field.unit else ''
        return '''<BsbTelegram %(src)d -> %(dst)d: %(packettype)s %(field)s = %(data)r%(unit)s [raw:%(rawdata)s]%(ts)s>'''%d

def runtest():
    fh = open('dump.txt', 'r')
    s = fh.read()
    fh.close()


    data = s.replace('\n','').replace(' ', '').decode('hex')
    result = BsbTelegram.deserialize(data)

    for r in result:
        print repr(r)

if __name__=='__main__':
    runtest()

