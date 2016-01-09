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

import time
import os


class SingleFieldLogger(object):
    _last_save_time = 0
    _last_saved_value = None
    _dtype = ''
    _last_was_value = False
    
    def __init__(o, field, interval=1, atomic_interval=1, send_get_telegram=None, filename=''):
        o.field = field
        o.interval = interval
        o.atomic_interval = atomic_interval
        o.send_get_telegram = send_get_telegram
        # list of fn(prev_val, this_val)
        o.triggers = []
        # list of timestamps when trigger was last fired.
        o.trigger_timestamps = []
        
        o.filename = filename or '%d.trace'%o.field.disp_id
        if not os.path.exists(filename):
            o.log_fieldname()
        o.log_interval()
        
    def add_trigger(o, callback, triggertype, param1=None, param2=None):
        '''callback: void fn()
        '''
        def fire_trigger(prev_val, this_val):
            callback(logger=o, 
                     triggertype=triggertype, 
                     param1=param1, 
                     param2=param2, 
                     prev_val=prev_val, 
                     this_val=this_val
            )
        
        if triggertype == 'rising_edge':
            def trigger(prev_val, this_val):
                if prev_val<=param1 and this_val>param1:
                    fire_trigger(prev_val, this_val)
                    return True
                return False
        elif triggertype == 'falling_edge':
            def trigger(prev_val, this_val):
                if prev_val>=param1 and this_val<param1:
                    fire_trigger(prev_val, this_val)
                    return True
                return False
        else:
            raise ValueError('bad trigger type %s'%triggertype)
        o.triggers.append(trigger)
        o.trigger_timestamps.append(0)
        
    def check_triggers(o, timestamp, prev_val, this_val):
        for n in range(len(o.triggers)):
            # dead time of 6 hrs after each trigger event!
            if timestamp >= 6*3600 + o.trigger_timestamps[n]:
                # trigger function returns True if trigger fired
                if o.triggers[n](prev_val, this_val):
                    o.trigger_timestamps[n] = timestamp
        
    def get_now(o):
        return o.atomic_interval * int(time.time() / o.atomic_interval)
        
    def tick(o):
        t = o.get_now()
        if t % o.interval == 0:
            o.send_get_telegram(o.field.disp_id)
            
    def log_value(o, timestamp, value):
        t = o.atomic_interval * int(timestamp  / o.atomic_interval)
        if t != o._last_save_time + o.interval:
            o.log_new_timestamp(t)
        else:
            o._last_save_time = t
            if o._last_saved_value is not None:
                o.check_triggers(t, o._last_saved_value, value)
        if o._last_saved_value is not None and value == o._last_saved_value:
            o._log_append('~', False)
        else:
            dtype = o.field.type_name
            if dtype != o._dtype:
                o._log_append(':dtype %s'%dtype)
                o._dtype = dtype
            o._log_append('%s'%_serialize_value(value, dtype))
        o._last_saved_value = value
            
    def log_fieldname(o):
        o._log_append(':disp_id %d'%o.field.disp_id)
        o._log_append(':fieldname %s'%o.field.disp_name.encode('utf8'))
        
    def log_interval(o):
        o._log_append(':interval %d'%o.interval)
            
    def log_new_timestamp(o, timestamp):
        o._log_append(':time %d'%timestamp)
        o._last_save_time = timestamp
    
    def _log_append(o, txt, linebreak_before=True):
        fh = open(o.filename, 'a')
        if linebreak_before or not o._last_was_value:
            txt = '\n'+txt
        fh.write(txt)
        fh.close()
        o._last_was_value = not (txt.startswith(':') or txt.startswith('\n:'))
        
def _serialize_value(val, dtype):
    if val is None:
        return '--'
    if dtype == '':
        # unknown field type, save raw hex code
        return ''.join(map(chr, val)).encode('hex')
    elif dtype in ['int16', 'temperature', 'int32']:
        return '%g'%val
    elif dtype == 'int8':
        return '%g'%val
    elif dtype == 'choice':
        return '%g'%val[0]
    elif dtype == 'time':
        return '%02.0d:%02.0d'%(val.hour, val.minute)
    else:
        raise ValueError('Cannot save values of type %s'%dtype)