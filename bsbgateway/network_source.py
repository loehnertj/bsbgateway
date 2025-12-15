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

import sys
import time
from threading import Thread
import socket

from .event_sources import EventSource


class NetworkSource(EventSource):
    """ A source for monitoring a TCP port. The TCP port is
        opened when the source is started.
        see also EventSource doc.

        event data are (timestamp, data) pairs, where data is a binary
            string representing the received data, and timestamp
            is seconds since epoch as returned by time.time().

        additionaly, a write() method is offered to write to the port.

        host: host address of the TCP to UART bridge
        port: TCP port to connect to.

        invert_bytes: invert bytes after reading & before sending (XOR with 0xFF)


        You will need a UART-to-TCP bridge to use this functionality.
        Communication has been tested and working with an esphome device using a
        "stream_server" external component.
        You can't directly connect an ESP to the BSB. Some "glue" electronics are
        needed as well. Set esphome RX/TX inversion according to your hardware
        (this is NOT BsbGateway's "invert_bytes")

        Abbreviated esphome config:

        esphome:
          name: elco-bsb
          friendly_name: ELCO BSB
          on_boot:
            - priority: 0
              then:
                - lambda: |-
                    id(bsb_uart).get_hw_serial()->setRxInvert(false);

        uart:
          - id: bsb_uart
            baud_rate: 4800
            parity: odd
            stop_bits: 1
            tx_pin:
              number: GPIO7
              inverted: true
            rx_pin:
              number: GPIO6
              inverted: true # will be "re-inverted" after boot; Arduino framework (which esphome is using) does not allow differing RX/TX inv settings on setup

        stream_server:
          id: uart_stream
          uart_id: bsb_uart
          port: 6638

        binary_sensor:
          - platform: stream_server
            id: uart_stream_connected
            name: Connected
            stream_server: uart_stream

    """
    def __init__(o,
        name,
        host,
        port,
        invert_bytes = False,
    ):
        o.name = name
        o.stoppable = True
        o.socket = None
        o._invert_bytes = invert_bytes

        o._host = host
        o._port = port


    def run(o, putevent_func):
        o.socket = socket.create_connection((o._host, o._port), timeout = 1)

        while True:
            # Reading 1 byte, followed by whatever is left in the
            # read buffer, as suggested by the developer of
            # PySerial.
            # read() blocks at most for (timeout)=1 second.
            try:
                data = o.socket.recv(2048)
            except TimeoutError:
                data = ''

            if o._stopflag:
                break

            if len(data) > 0:
                timestamp = time.time()
                if o._invert_bytes:
                    data = bytearray(data)
                    for i in range(len(data)):
                        data[i] ^= 0xff
                    data = bytes(data)
                putevent_func(o.name, (timestamp, data))

        o.socket.shutdown(SHUT_RDWR)
        o.socket.close()

    def write(o, data):
        if o._invert_bytes:
            data = bytearray(data)
            for i in range(len(data)):
                data[i] ^= 0xff
            data = bytes(data)

        o.socket.sendall(data)
