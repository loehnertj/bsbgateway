# -*- coding: utf8 -*-

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
sys.path.append(os.path.dirname(__file__))

import logging
log = lambda: logging.getLogger(__name__)

import time

from event_sources import SyncedSecondTimerSource, HubSource
from single_field_logger import SingleFieldLogger
from web_interface import WebInterface
from cmd_interface import CmdInterface
from email_action import make_email_action
from bsb.bsb_comm import BsbComm
from bsb.bsb_field import EncodeError, ValidateError


class BsbGateway(object):
    _hub = None

    def __init__(o, serial_port, device, bus_address, loggers, atomic_interval, web_interface_port=8080, cmd_interface_enable=True):
        o.device = device
        o._bsbcomm = BsbComm('bsb', serial_port, device, bus_address, n_addresses=3)
        o.loggers = loggers
        o.atomic_interval = atomic_interval
        o.web_interface_port = web_interface_port
        o.pending_web_requests = []
        o._cmd_interface_enable = cmd_interface_enable
        o.cmd_interface = None
        
    def run(o):
        log().info('BsbGateway (c) J. Loehnert 2013-2015, starting @%s'%time.time())
        for logger in o.loggers:
            logger.send_get_telegram = lambda disp_id: o._bsbcomm.send_get(disp_id)
        
        sources = [
            SyncedSecondTimerSource('timer'),
            o._bsbcomm,
        ]
        
        # Configuration switch tbd
        if o._cmd_interface_enable:
            o.cmd_interface = CmdInterface(o)
            sources.append(o.cmd_interface)
        else:
            log().info('Running without cmdline interface. Use Ctrl+C or SIGTERM to quit.')
        
        if o.web_interface_port:
            sources.append( WebInterface('web', device=o.device, port=o.web_interface_port) )
            
        o._hub = HubSource()
        for source in sources:
            o._hub.add_and_start_source(source)

        o._hub.start_thread(o._dispatch_event, new_thread=False)

    def _dispatch_event(o, evtype, evdata):
        try:
            getattr(o, 'on_%s_event'%evtype)(evdata)
        except Exception as e:
            log().exception('Something crashed while processing event {} with data {!r}'.format(evtype, evdata))

    def on_timer_event(o, data):
        if int(time.time()) % o.atomic_interval!=0:
            return
        for logger in o.loggers:
            logger.tick()
            
    def on_bsb_event(o, telegrams):
        for which_address, telegram in telegrams:
            if o.cmd_interface:
                if o._bsbcomm.sniffmode or which_address==1:
                    o.cmd_interface.filtered_print(which_address, telegram)
            if which_address==0 and telegram.packettype == 'ret':
                for logger in o.loggers:
                    if logger.field.disp_id == telegram.field.disp_id:
                        logger.log_value(telegram.timestamp, telegram.data)
            if which_address==2 and telegram.packettype in ['ret', 'ack']:
                key = '%s%d'%(telegram.packettype, telegram.field.disp_id)
                for rq in o.pending_web_requests:
                    if rq[0] == key:
                        o.pending_web_requests.remove(rq)
                        rq[1].put(telegram)
                        
    def on_web_event(o, request):
        # FIXME: rate limit 10/s
        rq = request.pop(0) # the result queue
        action = request.pop(0)
        if action == 'get':
            disp_id = request[0]
            o.pending_web_requests.append(('ret%d'%disp_id, rq))
            try:
                o._bsbcomm.send_get(disp_id, 2)
            except (ValidateError, EncodeError) as e:
                rq.put(e)
        elif action == 'set':
            disp_id, value = request
            o.pending_web_requests.append(('ack%d'%disp_id, rq))
            try:
                o._bsbcomm.send_set(disp_id, value, 2)
            except (ValidateError, EncodeError) as e:
                rq.put(e)
        else:
            raise ValueError('unsupported action')
        
    def quit(o):
        o._hub.stop()
        
    def cmdline_get(o, disp_id):
        o._bsbcomm.send_get(disp_id, 1)
        
    def cmdline_set(o, disp_id, value, validate=True):
        o._bsbcomm.send_set(disp_id, value, 1, validate=validate)
        
    def set_sniffmode(o, sniffmode=False):
        o._bsbcomm.sniffmode = sniffmode
        

def run(config):
    # FIXME: make this a dynamic import.
    if config['device'] == 'broetje_isr_plus':
        import bsb.broetje_isr_plus as device
    else:
        raise ValueError('Unsupported device')
    
    emailaction = make_email_action(config['emailserver'], config['emailaddress'], config['emailcredentials'])
    loggers = [
        SingleFieldLogger(
            field=device.fields[disp_id],
            interval=interval, 
            atomic_interval=config['atomic_interval'],
            filename=os.path.join(config['tracefile_dir'], '%d.trace'%disp_id)
        ) 
        for disp_id, interval in config['loggers']
    ]
    for trigger in config['triggers']:
        disp_id = trigger[0]
        for logger in loggers:
            if logger.disp_id == disp_id:
                logger.add_trigger(emailaction, *trigger[1:])
                
    BsbGateway(
        serial_port=config['serial_port'],
        device=device,
        bus_address=config['bus_address'],
        loggers=loggers,
        atomic_interval=config['atomic_interval'],
        web_interface_port=(config['web_interface_port'] if config['web_interface_enable'] else None),
        cmd_interface_enable=config['cmd_interface_enable']
    ).run()