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

import re
import time
import datetime
from traceback import format_exc

from event_sources import StdinSource, SyncedSecondTimerSource, HubSource
from bsb.bsb_comm import BsbComm
from bsb.bsb_field import EncodeError, ValidateError, BsbFieldChoice, BsbFieldInt8, BsbFieldInt16, BsbFieldTime
from bsb.bsb_fields import groups, fields
from single_field_logger import SingleFieldLogger
from web_interface import WebInterface
from email_action import make_email_action



CMDS = [
    {
        'cmd': 'quit',
        're': r'q(uit)?',
        'help': 'quit - what it says',
    }, {
        'cmd': 'help',
        're': r'h(elp)?(\s+(?P<cmd>[a-z]+))?',
        'help': 'help [<cmd>] - help on specific command, without cmd = this message'
    }, {
        'cmd': 'get',
        're': r'g(et)?\s+(?P<disp_id>[0-9]+)',
        'help': '''get <field> - request value of field with ID <field> once (without logging)
            field id = the value as seen on the standard LCD display.
        ''',
    }, {
        'cmd': 'set',
        're': r's(et)?\s+(?P<disp_id>[0-9]+)\s(?P<value>[0-9.:-]+)\s*(?P<use_force>[!]?)',
        'help': '''set <field> <value>[!]- set value of field with ID <field>.
            field id = the value as seen on the standard LCD display.
            value = 
                    | number e.g. "0", "1.1", "-5"
                    | time e.g. "08:30"
                    | choice index e.g. "2"
                    | "--" (not set)
                (each time without quotes) depending on field.
            "!" after the value disables validation (bounds checking). USE AT YOUR OWN RISK.
        ''',
    }, {
        'cmd': 'dump',
        're': r'd(ump)?\s*(?P<mode>on|off|all)?',
        'help': '''dump [off|on|all] - dump (print here) received data?
            off = dump nothing
            on = dump return messages sent to me
            all = dump everything that goes over the bus
        without argument, toggle between on and off.
        note: resets the filter.
        '''
    }, {
        'cmd': 'filter',
        're': r'f(ilter)?\s*(?P<expr>.*)',
        'help': '''filter [<expr>] - dump received data matching the filter.
            <expr> is a python expression* which can combine the following variables:
                src - source bus address ex. src=10
                dst - destination bus address ex. dst=0
                field - disp id of field ex. field=8510
                fieldhex - hex (bus visible) id of field ex. fieldhex=0x493d052a
                type - ret, get, set, ack, inf ex. type=ack
            ... and must return True or False.
            use "filter" without arg or "filter off" to disable.
            notes:
                * in the expression you can use = instead of == for comparison.
                This command sets dump mode=all.
        '''
    }, {
        'cmd': 'list',
        're': r'l(ist)?\s*(?P<hash>#)?(?P<text>[^+]*)(?P<expand>\+)?',
        'help': '''list [#][<text>][+]: list field groups.
            list:
                lists all known groups (menus)
            list #<text>:
                lists all groups (menus) containing the text. If only a single group matches, lists its fields.
            list <text>:
                lists all fields whose name contains the text.
            list+ or list #<text>+: forces expanded view (include field lists).
'''
    }, {
        'cmd': 'info',
        're': r'i(nfo)?\s*?(?P<ids>[0-9 ]+)?',
        'help': '''info <id>[, <id>...]: print field descriptions for the given field ids (4-digit numbers).
'''
    }
]


class BsbGateway(object):
    _hub = None
    _bsbcomm = None
    _dump = 'off'
    _dump_filter = 'True'

    def __init__(o, serial_port, bus_address, loggers, atomic_interval):
        o._bsbcomm = BsbComm('bsb', serial_port, bus_address, n_addresses=3)
        o.loggers = loggers
        o.atomic_interval = atomic_interval
        o.pending_web_requests = []
        
    def run(o):
        for logger in o.loggers:
            logger.send_get_telegram = lambda disp_id: o._bsbcomm.send_get(disp_id)
        
        sources = [
            StdinSource('stdin'),
            SyncedSecondTimerSource('timer'),
            WebInterface('web'),
            o._bsbcomm,
        ]
        o._hub = HubSource()
        for source in sources:
            o._hub.add_and_start_source(source)

        o.cmd_help()
        o._hub.start_thread(o._dispatch_event, new_thread=False)

    def _dispatch_event(o, evtype, evdata):
        try:
            getattr(o, 'on_%s_event'%evtype)(evdata)
        except Exception as e:
            log().exception('Something crashed while processing event {} with data {!r}'.format(evtype, evdata))

    def on_stdin_event(o, line):
        line = line[:-1] # crop newline
        for cmd in CMDS:
            m = re.match(cmd['re'], line, re.I)
            if m:
                # call o.cmd_whatever with named groups as kwargs
                getattr(o, 'cmd_' + cmd['cmd'])(**m.groupdict())
                break
        else:
            print 'Unrecognized command.'

    def on_timer_event(o, data):
        if int(time.time()) % o.atomic_interval!=0:
            return
        for logger in o.loggers:
            logger.tick()
            
    def on_bsb_event(o, telegrams):
        for which_address, telegram in telegrams:
            if o._dump!='off' or which_address==1:
                try:
                    ff = eval(o._dump_filter, {}, {
                        'src':telegram.src, 'dst':telegram.dst, 'type': telegram.packettype,
                        'field': telegram.field.disp_id, 'fieldhex': telegram.field.telegram_id,
                        'inf':'inf', 'get':'get', 'ret':'ret', 'set':'set', 'ack':'ack'
                    })
                except Exception as e:
                    logging.error('error applying filter: %r'%e)
                    ff = False
                if which_address==1 or ff is True:
                    print repr(telegram)
            if which_address==0 and telegram.packettype == 'ret':
                for logger in o.loggers:
                    if logger.disp_id == telegram.field.disp_id:
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
                        
    def cmd_quit(o):
        o._hub.stop()
                        
    def cmd_get(o, disp_id):
        disp_id = int(disp_id)
        try:
            o._bsbcomm.send_get(disp_id, 1)
        except (ValidateError, EncodeError) as e:
            print e.__class__.__name__ +': '+ str(e)
        
    def cmd_set(o, disp_id, value, use_force):
        try:
            disp_id = int(disp_id)
            field = fields[disp_id]
        except (TypeError, ValueError, KeyError):
            print 'Unrecognized field.'
            return
        if value == '--':
            value = None
        else:
            try:
                if isinstance(field, (BsbFieldChoice, BsbFieldInt8)):
                    value = int(value)
                elif isinstance(field, BsbFieldInt16):
                    value = float(value)
                elif isinstance(field, BsbFieldTime):
                    value = datetime.time(*map(int, value.split(':')))
                else:
                    raise TypeError('Data type for field %s %s is not defined.'%(field.disp_id, field.disp_name))
            except (TypeError, ValueError) as e:
                print e
                return
        try:
            o._bsbcomm.send_set(field.disp_id, value, 1, validate=(use_force!='!'))
        except (ValidateError, EncodeError) as e:
            logging.error(e)
        
    def cmd_dump(o, mode=None):
        if mode:
            if mode not in ['on', 'off', 'all']:
                return 'unknown dump mode "%s"'%mode
            o._dump = mode
            o._bsbcomm.sniffmode = (mode=='all')
        else:
            o._dump = 'on' if o._dump=='off' else 'off'
            o._bsbcomm.sniffmode = False
            print 'dump is now %s'%o._dump
        o._dump_filter = 'True'
            
    def cmd_filter(o, expr='off'):
        if expr in [None, '', 'off']:
            expr = 'True'
        expr = expr.replace('=', '==')
        expr = expr.replace('>==', '>=').replace('<==', '<=')
        
        try:
            x = eval(expr, {}, {
                'src':0, 'dst':0, 'field':0, 'fieldhex':0, 'type':0,
                'inf':'inf', 'ret':'ret', 'get':'get', 'ack':'ack', 'set':'set'
            })
        except:
            print 'bad filter expression'
            return
        o._dump_filter = expr
        o._dump = 'all'
        o._bsbcomm.sniffmode=True
        
    def cmd_list(o, text='', hash='', expand=''):
        '''list [<text>][+]: list field groups.
            list:
                lists all known groups (menus)
            list #<text>:
                lists all groups (menus) containing the text. If only a single group matches, lists its fields.
            list <text>:
                lists all fields whose name contains the text.
            list+ or list #<text>+: forces expanded view (include field lists).
'''
        hash = bool(hash)
        expand = bool(expand)
        text = text.lower()
        if not text: hash=True
        if hash:
            grps = [grp
                    for grp in groups
                    if text in grp.name.lower()
            ]
        else:
            grps = groups
        if len(grps) == 0:
            print 'Not found.'
            return
        # expand if searching in field names or if only one group was found.
        if (text and not hash) or len(grps)==1:
            expand = True
            
        for grp in grps:
            if not expand:
                print '#'+grp.name
            else:
                flds = grp.fields
                if text and not hash:
                    flds = [f for f in flds if text in f.disp_name.lower()]
                flds.sort(key=lambda x: (x.disp_id, x.telegram_id))
                if flds:
                    print '#'+grp.name+':'
                    for f in flds:
                        print '    '+f.short_description
                    print
            
    def cmd_info(o, ids=''):
        '''info <id>[, <id>...]: print field descriptions for the given field ids (4-digit numbers).'''
        ids = [int(id) for id in ids.split(' ') if id!='']
        try:
            ll = [fields[id] for id in ids]
        except KeyError:
            print 'Not found.'
            return
        ll.sort(key=lambda x: (x.disp_id, x.telegram_id))
        for field in ll:
            print field.long_description
            print

    def cmd_help(o, cmd=''):
        if not cmd:
            print '''BsbGateway v0.1 (c) 2013-2015 J. Löhnert
Commands: (every command can be abbreviated to just the first character)
    
%s

'''%(
                '\n'.join((cmd['help'].split('\n')[0] for cmd in CMDS)),
            )
        else:
            cmd = [c for c in CMDS if c['cmd'].startswith(cmd)]
            if not cmd:
                print 'Unknown command.'
            else:
                print cmd[0]['help']
                

def run(config):
    emailaction = make_email_action(config['emailserver'], config['emailaddress'], config['emailcredentials'])
    loggers = [
        SingleFieldLogger(
            disp_id=disp_id, 
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
    
    BsbGateway(config['serial_port'], config['bus_address'], loggers, config['atomic_interval']).run()