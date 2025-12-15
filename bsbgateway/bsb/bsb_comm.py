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
log = lambda: logging.getLogger(__name__)

from contextlib import contextmanager
import threading
import queue
import time

# FIXME: importing from parent, this smells bad
from bsbgateway.event_sources import EventSource
from bsbgateway.serial_source import SerialSource
from bsbgateway.network_source import NetworkSource

from .bsb_telegram import BsbTelegram
from .bsb_field import ValidateError, EncodeError

MAX_PENDING_REQUESTS = 50

class BsbComm(EventSource):
    '''simplifies the conversion between serial data and BsbTelegrams.
    BsbComm represents one or multiple BSB bus endpoint(s). You can
    send and receive BsbTelegrams.

    Wrapper around the serial or network source: instead of raw data,
    the parsed telegrams are returned. Event payload is a list of tuples:
        [(which_address, BsbTelegram), (which_address, BsbTelegram) ...].
    which address gives the index of the bus address where the telegram came in
    (0 for first) - None if the telegram was not intended for this endpoint.

    Functions for sending:
        * send_get: sends a telegram requesting the disp_id's value
        * send_set: sends a telegram setting the value for disp_id.

    Also supports sniffing (i.e. catching messages for other endpoints).
    Set sniffmode=True for this. Can be toggled while running.
    '''
    bus_addresses = []
    # set to true to return ALL telegrams going over the bus (not just those meant for me)
    sniffmode = False
    _leftover_data = b''

    def __init__(o, name, comm_interface, device, first_bus_address, n_addresses=1, sniffmode=False, min_wait_s=0.1):
        if (first_bus_address<=10):
            raise ValueError("First bus address must be >10.")
        if (first_bus_address+n_addresses>127):
            raise ValueError("Last bus address must be <128.")

        if (comm_interface['type'] == 'serial'):
            adapter_settings = comm_interface['adapter_settings']
            o.comm_interface = SerialSource(
                name=name,
                port_num=adapter_settings['adapter_device'],
                # use sane default values for the rest if not set
                port_baud=adapter_settings.get('port_baud', 4800),
                port_stopbits=adapter_settings.get('port_stopbits', 1),
                port_parity=adapter_settings.get('port_parity', 'odd'),
                # Most simple RS232 level converters will deliver inverted bytes.
                invert_bytes=adapter_settings.get('invert_bytes', True),
                expect_cts_state=adapter_settings.get('expect_cts_state', None),
                write_retry_time=adapter_settings.get('write_retry_time', 0.005),
            )
        elif (comm_interface['type'] == 'network'):
            network_settings = comm_interface['network_settings']
            o.comm_interface = NetworkSource(
                name = name,
                host = network_settings['host'],
                port = network_settings['port'],
                # Most simple RS232 level converters will deliver inverted bytes, which will be transmitted like that over TCP.
                invert_bytes = network_settings.get('invert_bytes', True),
            )
        else:
            raise IOError("Invalid comm_interface type")

        o.device = device
        o.bus_addresses = range(first_bus_address, first_bus_address+n_addresses)
        o._leftover_data = b''
        o.sniffmode = sniffmode
        o.min_wait_s = min_wait_s
        o._do_throttled = None

    def run(o, putevent_func):
        def convert_data(name, data):
            # data = timestamp,bytes
            telegrams = o.process_received_data(data[0], data[1])
            putevent_func(name, telegrams)
        with throttle_factory(min_wait_s=o.min_wait_s) as do_throttled:
            o._do_throttled = do_throttled
            o.comm_interface.run(convert_data)
        o._do_throttled = None

    def process_received_data(o, timestamp, data):
        '''timestamp: unix timestamp
        data: incoming data (byte string) from the comm_interface
        return list of (which_address, telegram)
        if promiscuous=True:
            all telegrams are returned. Telegrams not for me get which_address=None.
        else:
            Only telegrams that have the right bus address and packettype 7 (return value)
            are included in the result.
        '''
        telegrams = BsbTelegram.deserialize(o._leftover_data + data, o.device)
        result = []
        if not telegrams:
            return
        # junk at the end? remember, it could be an incomplete telegram.
        leftover = b''
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
                log().info('++++%r :: %s'%t )
        return result

    def send_get(o, disp_id, which_address=0):
        '''sends a GET request for the given disp_id.
        which_address: which busadress to use, default 0 (the first)'''
        if disp_id not in o.device.fields:
            raise EncodeError('unknown field')
        t = BsbTelegram()
        t.src = o.bus_addresses[which_address]
        t.dst = 0
        t.packettype = 'get'
        t.field = o.device.fields[disp_id]
        o._send_throttled(t.serialize())

    def send_set(o, disp_id, value, which_address=0, validate=True):
        '''sends a SET request for the given disp_id.
        value is a python value which must be appropriate for the field's type.
        which_address: which busadress to use, default 0 (the first).
        validate: to disable validation, USE WITH EXTREME CARE.
        '''
        if disp_id not in o.device.fields:
            raise EncodeError('unknown field')
        t = BsbTelegram()
        t.src = o.bus_addresses[which_address]
        t.dst = 0
        t.packettype = 'set'
        t.field = o.device.fields[disp_id]
        t.data = value
        # might throw ValidateError or EncodeError.
        data = t.serialize(validate=validate)
        o._send_throttled(data)

    def _send_throttled(o, data:bytes):
        if not o._do_throttled:
            raise IOError("Cannot send: Not running")
        o._do_throttled(lambda: o.comm_interface.write(data))


@contextmanager
def throttle_factory(min_wait_s = 0.1, max_pending_requests=MAX_PENDING_REQUESTS):
    """Throttled action.

    Contextmanager yields a function ``do_throttled(action)``.

    Calling it will schedule a call of ``action()``, which can be whatever you want..

    Multiple action(s) are executed sequentially, and there is a minimum time of
    ``min_wait_s`` between *end* of last and *start* of next action.

    To achieve this, a separate thread is used, which is automatically started
    and stopped.
    """
    stop = threading.Event()
    todo = queue.Queue(maxsize=max_pending_requests)

    def runner():
        action = None
        while not stop.is_set():
            if action is not None:
                try:
                    action()
                except Exception:
                    log().error("Exception in throttle thread", exc_info=True)
            action_end_time = time.time()
            action = todo.get()
            # Throttle using wallclock time
            # If todo.get() blocked for longer than min_wait_s, do not wait.
            wait_for = action_end_time + min_wait_s - time.time()
            if wait_for > 0.0:
                log().debug("throttle: wait %s seconds", wait_for)
                stop.wait(wait_for)

    def do_throttled(action):
        try:
            todo.put(action, timeout=0)
        except queue.Full as e:
            raise RuntimeError("Too many requests at once!") from e

    thread = threading.Thread(target=runner, name="throttled_runner")
    thread.start()
    try:
        yield do_throttled
    finally:
        stop.set()
        # Unblock todo.get()
        todo.put(lambda:None)
