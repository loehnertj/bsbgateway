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

from serial import SerialBase, PortNotOpenError
from threading import Event, Lock

def default_responder():
    txdata = b''
    while True:
        rxdata = yield txdata
        txdata = rxdata

class VirtualSerial(SerialBase):
    """A Serialport-compatible class for simulation and testing.

    The given ``responder`` shall be a two-way generator function.

    It will receive Write-data immediately, and shall yield returndata.

    Multipart responses are currently unsupported.

    Example responder::

        def default_responder():
            txdata = b''
            while True:
                rxdata = yield txdata
                txdata = rxdata

    """
    def __init__(self, *args, responder=default_responder, **kwargs):
        self.responder = responder
        super().__init__(*args, **kwargs)

    def do_nothing(self):
        pass

    @property
    def in_waiting(self):
        return len(self._rxdata)

    @property
    def out_waiting(self):
        return 0

    def open(self):
        # Start handler
        self._handler = self.responder()
        self._rxdata = b''
        self._has_rxdata = Event()
        next(self._handler)
        self.is_open = True
        self._handling_lock = Lock()

    def close(self):
        self.cancel_read()
        self._handler.close()
        self.is_open = False

    def _reconfigure_port(self):
        pass

    def read(self, size=1):
        buf = b''
        while len(buf) < size:
            if not self.is_open:
                raise PortNotOpenError()
            # FIXME: Timeout is applied multiple times if getting partial results
            self._has_rxdata.wait(self._timeout)
            if not self._rxdata:
                # read Aborted
                return buf
            if not self.is_open:
                return buf
            need = size - len(buf) 
            take, keep = self._rxdata[:need], self._rxdata[need:]
            self._rxdata = keep
            if len(self._rxdata) == 0:
                self._has_rxdata.clear()
            buf += take
        return buf

    def reset_input_buffer(self):
        self._rxdata = b''
        self._has_rxdata.clear()

    def cancel_read(self):
        self._rxdata = b''
        self._has_rxdata.set()

    def write(self, data):
        # immediately receive response
        with self._handling_lock:
            self._rxdata += self._handler.send(data)
            if self.in_waiting > 0:
                self._has_rxdata.set()

    reset_output_buffer = do_nothing
    cancel_write = do_nothing
    flush = do_nothing
    send_break = do_nothing
    _update_break_state = _update_rts_state = _update_dtr_state = do_nothing
