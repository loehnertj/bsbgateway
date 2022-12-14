##############################################################################
#
#    Part of BsbGateway
#    Copyright (C) Johannes Loehnert, 2013-2022
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

import sys
import logging
log = lambda: logging.getLogger(__name__)
import datetime
import time

from .bsb.bsb_telegram import BsbTelegram
from .bsb import broetje_isr_plus

if sys.version_info[0] == 2:
    ashex = lambda b: b.encode('hex')
else:
    ashex = lambda b: b.hex()

def invert(data):
    return bytes(x ^ 0xff for x in data)


def virtual_device(device=broetje_isr_plus):
    # TODO: uninvert bytes
    txdata = b''
    state = {}
    while True:
        rxdata = yield txdata
        log().debug('Virtual device receives: [%s]'%(ashex(rxdata)))

        # read back written data (as the real bus adapter does)
        txdata = rxdata

        maybe_inv = invert if (rxdata.startswith(b'\x23')) else lambda x:x

        # construct response
        rxdata = maybe_inv(rxdata)
        t = BsbTelegram.deserialize(rxdata, device)[0]
        log().debug("decoded packet: %s", t)
        if isinstance(t, tuple):
            # Bad packet. Do not send a response
            continue

        # remember set value for session
        if t.packettype == 'set':
            log().debug('cached value of %r'%(t.data,))
            state[t.field.disp_id] = t.data
        t.src, t.dst = t.dst, t.src
        data = rxdata
        t.packettype = {'set':'ack', 'get':'ret'}[t.packettype]
        # for GET, return current state if set, else default value dep. on field type.
        if t.packettype == 'ret':
            try:
                t.data = state[t.field.disp_id]
            except KeyError:
                t.data = {
                    'choice': 1,
                    'time': datetime.time(13,37),
                }.get(t.field.type_name, 42)
        retdata = t.serialize(validate=False)
        retdata = maybe_inv(retdata)

        time.sleep(0.1)
        log().debug('Virtual device returns : [%s]'%ashex(retdata))
        txdata += retdata
