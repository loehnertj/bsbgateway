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
import os
up = os.path.dirname
sys.path.append(up(up(__file__)))

import logging
log = lambda: logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

import templates

import time

from Queue import Queue
from . import WebInterface

class FakeField(object):
    def __init__(o):
        o.telegram_id = 0xDEADBEEF
        o.disp_id = 1234
        o.disp_name = u'Fake Field'
        o.unit = ''
        o.rw = True
        o.nullable = True

class FakeTelegram(object):
    def __init__(o):
        o.src = 0
        o.dst = 25
        o.packettype = 'ret'
        o.rawdata = [0, 42]
        o.data = 42
        o.field = FakeField()
        o.timestamp = time.time()

class BroetjeResponder(object):
    def on_event(o, evtype, evdata):
        if evtype == 'web':
            rq = evdata.pop(0)
            subtype = evdata.pop(0)
            rq.put(getattr(o, 'web_'+subtype)(*evdata))
            
    def web_get(o, disp_id):
        t = FakeTelegram()
        t.field.disp_id = disp_id
        return t
    
    def web_set(o, disp_id, value):
        t = FakeTelegram()
        t.packettype = 'ack'
        t.field.disp_id = disp_id
        return t

wi = WebInterface()
br = BroetjeResponder()
wi.start_thread(br.on_event)

log().warning('Running standalone test server with a mock backend. Press Enter to exit.')
# Nothing to do on this thread anymore. Wait.
raw_input()
log().info('Goodbye...')