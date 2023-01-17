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
from queue import Empty
import datetime
import web

from bsbgateway.bsb.bsb_field import ValidateError, EncodeError
from .webutils import bridge_call
from .templates import tpl

_ERRHEADERS = {
    'Content-Type': 'text/plain; charset=utf-8',
}

        
class Field(object):
    url = r'field-([0-9]+)(?:\.([a-zA-Z]+))?'
    def __init__(o):
        fields = web.ctx.bsb.fields
        o.parameters={
            'field': lambda x: fields[int(x)],
            'value': lambda x: None if x in ('', '--') else float(x),
            'hour': lambda x: None if x in ('', '--') else int(x),
            'minute': lambda x: None if x in ('', '--') else int(x),
        }
    
    def GET(o, disp_id, view=None):
        q = web.input()
        q.update({'field': disp_id})
        
        if view:
            return bridge_call(o, view, q, o.parameters)
        else:
            field = web.ctx.bsb.fields[int(disp_id)]
            return tpl.base(bridge_call(o, 'fragment', q, o.parameters), '{} {}'.format(field.disp_id, field.disp_name))
        
    def POST(o, disp_id, view=None):
        q = web.input()
        q.update({'field': disp_id})
        
        try:
            return bridge_call(o, 'setvalue', q, o.parameters)
        except (ValidateError, EncodeError, ValueError) as e:
            web.header('Content-Type', 'text/html; charset=utf-8')
            return '%s: %s'%(e.__class__.__name__, e)
        
    def fragment(o, field):
        return tpl.field(o, field)
    
    def widget(o, field):
        val = o.value(field)['data']
        return tpl.field_widget(o, field, val)
            
    def value(o, field):
        # sends event to the BsbGateway requesting field's value.
        queue = web.ctx.bsb.get(field.disp_id)
        # blocks until result is available
        try:
            # Internal timeout is 3.0s, give some additional time for crossthreading
            t = queue.get(timeout=4.0)
        except Empty:
            log().error('timeout while requesting value')
            raise web.HTTPError("500", headers=_ERRHEADERS, data="Data query from heater timed out.")
        if t is None:
            raise web.notfound()
        if isinstance(t, Exception):
            # FIXME: web error should not be raised here
            log().error('error while requesting value: %s: %s', t.__class__.__name__, str(t))
            raise web.HTTPError("500", headers=_ERRHEADERS, data=str(t))
        
        data = t.data
        if hasattr(data, 'hour'):
            data = (data.hour, data.minute)
        return {
            'disp_id': t.field.disp_id,
            'disp_name': t.field.disp_name,
            'timestamp': t.timestamp,
            'data': data,
        }
    
    def setvalue(o, field, value=None, hour=None, minute=None):
        if field.type_name=='time':
            if hour is None or minute is None:
                value = None
            else:
                value = datetime.time(hour, minute)
        if field.type_name in ['int8', 'choice']:
            if value is not None:
                value = int(value)
        field.validate(value)
        log().info('set field %d to value %r'%(field.disp_id, value))
        queue = web.ctx.bsb.set(field.disp_id, value)
        try:
            # Internal timeout is 3.0s, give some additional time for crossthreading
            t = queue.get(timeout=4.0)
        except Empty:
            log().error('timeout while setting value')
            raise web.HTTPError("500", headers=_ERRHEADERS, data="Data request to heater timed out.")
        if t is None:
            raise web.notfound()
        if isinstance(t, Exception):
            log().error('error while setting value: %s: %s', t.__class__.__name__, str(t))
            raise web.HTTPError("500", headers=_ERRHEADERS, data=str(t))
        # FIXME?
        return 'OK'
    
    def fmt_rovalue(o, field, value):
        if field.type_name == 'choice':
            return "%d %s"%value
        elif field.type_name == 'time':
            return "%0.2d:%0.2d"%value
        elif field.type_name == '':
            dez = ' '.join(map(str, value))
            hx = ' '.join(['%x'%num for num in value])
            return "dec: %s / hex: %s"%(dez, hx)
        else:
            return "%g %s"%(value, field.unit)
        
    def fmt_range(o, field):
        if field.type_name in ('int16', 'temperature', 'int32'):
            mn, mx = field.min/field.divisor, field.max/field.divisor
        else:
            mn, mx = field.min, field.max
        return '(%g ... %g)'%(mn, mx)
