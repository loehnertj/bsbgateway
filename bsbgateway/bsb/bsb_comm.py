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

import logging
from event_sources import EventSource
from serial_source import SerialSource
from fake_serial_source import FakeSerialSource

from bsb_telegram import BsbTelegram
from bsb_field import ValidateError, EncodeError
from bsb_fields import fields

class BsbComm(EventSource):
    '''simplifies the conversion between serial data and BsbTelegrams.
    BsbComm represents one or multiple BSB bus endpoint(s). You can
    send and receive BsbTelegrams. 
    
    Wrapper around the serial source: instead of raw data,
    the parsed telegrams are returned. Event payload is a list of tuples:
        [(which_address, BsbTelegram), (which_address, BsbTelegram) ...].
    which address gives the index of the bus address where the telegram came in
    (0 for first) - None if the telegram was not intended for this endpoint.
    
    Functions for sending:
        * send_get: sends a telegram requesting the disp_id's value
        * send_set: TODO
        
    Also supports sniffing (i.e. catching messages for other endpoints). 
    Set sniffmode=True for this. Can be toggled while running.
    '''
    bus_addresses = []
    # set to true to return ALL telegrams going over the bus (not just those meant for me)
    sniffmode = False
    _leftover_data = ''
    
    def __init__(o, name, port, first_bus_address, n_addresses=1, sniffmode=False):
        if (first_bus_address<=10):
            raise ValueError("First bus address must be >10.")
        if (first_bus_address+n_addresses>127):
            raise ValueError("Last bus address must be <128.")
        if port=='fake':
            o.serial = FakeSerialSource(name=name)
        else:
            o.serial = SerialSource(
                name=name,
                port_num=port,
                port_baud=4800,
                port_stopbits=1,
                port_parity='odd',
                invert_bytes=True,
                expect_cts_state=False,
                write_retry_time=0.005
            )
        o.bus_addresses = range(first_bus_address, first_bus_address+n_addresses)
        o._leftover_data = ''
        o.sniffmode = sniffmode
        
    def run(o, putevent_func):
        def convert_data(name, data):
            # data = timestamp,bytes
            telegrams = o.process_received_data(data[0], data[1])
            putevent_func(name, telegrams)
        o.serial.run(convert_data)
        
        
    def process_received_data(o, timestamp, data):
        '''timestamp: unix timestamp
        data: incoming data (byte string) from the serial port
        return list of (which_address, telegram)
        if promiscuous=True:
            all telegrams are returned. Telegrams not for me get which_address=None.
        else:
            Only telegrams that have the right bus address and packettype 7 (return value)
            are included in the result.
        '''
        telegrams = BsbTelegram.deserialize(o._leftover_data + data)
        result = []
        if not telegrams:
            return
        # junk at the end? remember, it could be an incomplete telegram.
        leftover = ''
        for data in reversed(telegrams):
            if isinstance(data, BsbTelegram):
                break
            leftover = data[0] + leftover
        o._leftover_data = leftover

        for t in telegrams:
            if isinstance(t, BsbTelegram):
                t.timestamp = timestamp
                if t.dst in o.bus_addresses or o.sniffmode:
                    try:
                        which_address = o.bus_addresses.index(t.dst)
                    except ValueError:
                        which_address = None
                    result.append((which_address, t))
            elif t[1] != 'incomplete telegram':
                logging.info('++++%r :: %s'%t )
        return result
                
    def send_get(o, disp_id, which_address=0):
        '''sends a GET request for the given disp_id.
        which_address: which busadress to use, default 0 (the first)'''
        if disp_id not in fields:
            raise EncodeError('unknown field')
        t = BsbTelegram()
        t.src = o.bus_addresses[which_address]
        t.dst = 0
        t.packettype = 'get'
        t.field = fields[disp_id]
        o.serial.write(t.serialize())

    def send_set(o, disp_id, value, which_address=0, validate=True):
        '''sends a SET request for the given disp_id.
        value is a python value which must be appropriate for the field's type.
        which_address: which busadress to use, default 0 (the first).
        validate: to disable validation, USE WITH EXTREME CARE.
        '''
        if disp_id not in fields:
            raise EncodeError('unknown field')
        t = BsbTelegram()
        t.src = o.bus_addresses[which_address]
        t.dst = 0
        t.packettype = 'set'
        t.field = fields[disp_id]
        t.data = value
        # might throw ValidateError or EncodeError.
        data = t.serialize(validate=validate)
        o.serial.write(data)
        