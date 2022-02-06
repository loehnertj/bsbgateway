# -*- coding:utf8 -*-

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
from datetime import time

__all__ = ['EncodeError', 'ValidateError', 
           'BsbField', 'BsbFieldChoice', 'BsbFieldInt8', 'BsbFieldInt16',
           'BsbFieldTemperature', 'BsbFieldInt32',
           'BsbFieldTime',
           ]

if sys.version_info[0] > 2:
    basestring = str


class EncodeError(Exception): pass
class ValidateError(Exception): pass

def xo(dict):
    return {k:v for k,v in dict.items() if k!='o'}

class BsbField(object):
    type_name=''
    type_description = u'Unknown type'
    def __init__(o, telegram_id, disp_id, disp_name, unit=u'', rw=False, nullable=False, tn="", *args, **kwargs):
        o.telegram_id = telegram_id
        o.disp_id = disp_id
        o.disp_name = disp_name
        o.unit = unit
        o.rw = rw
        o.nullable = nullable
        o.new_type_name = tn
        
    # Override these 3 ...
    def _decode_data(o, rawdata):
        '''turns the bytes in rawdata into a python value.'''
        return rawdata
    def _encode_data(o, data, flag):
        '''turns the python value in data into bytes for sending.
        Must check that the data can be turned into valid bytes and raise EncodeError on fail.
        Flag is the first byte and depends on packettype and whether field is nullable.'''
        raise EncodeError('Field %s: Unknown field type, value cannot be encoded.'%o.disp_id)
    
    def _validate_data(o, data):
        '''validates that data adheres to the constraints of the particular field.
        users should call validate(data), which takes care of the rw and nullable flags.
        Should raise ValidateError on fail.
        '''
        raise ValidateError('Field %s: Unknown field type, value cannot be validated.'%o.disp_id)
    
    def validate(o, data):
        '''Validates that the given data is valid within the field's defined constraints,
        and raises ValidateError if not.'''
        if not o.rw:
            raise ValidateError('Field %s is read-only.'%o.disp_id)
        if data is None:
            if not o.nullable:
                raise ValidateError('Null value not allowed for field %s.'%o.disp_id)
        else:
            return o._validate_data(data)
        
    def encode(o, data, packettype, validate=True):
        '''Encodes the given data into a list of bytes.
        By default, validates before encoding, raising ValidateError on invalid data.
        
        If validation is turned off, you can give any value which can be sensibly turned 
        into bytes (for example a time of 255:255). Send to your device on your own risk.
        
        Raises ValueError if the data cannot be turned into bytes.
        '''
        if validate:
            o.validate(data)
        return o._encode_data(data, o._valueflag(data, packettype))
    
    def decode(o, rawdata):
        if len(rawdata) < 1:
            raise ValueError('Packet contains no data.')
        if o.nullable:
            if rawdata[0] in [1, 5]:
                return None
        try:
            return o._decode_data(rawdata)
        except Exception as e:
            print('BsbField.decode: %r' % (e,))
            return None
            
    
    def _valueflag(o, val, packettype):
        '''returns the valueflag (first byte of value) to be set.
        '''
        if packettype == 'ret':
            return 1 if val is None else 0
        elif packettype == 'set':
            if o.nullable:
                return 5 if val is None else 6
            else:
                if val is None: raise EncodeError('Cannot encode Null value for non-nullable field %s.'%o.disp_id)
                return 1
        else:
            raise EncodeError('Can only encode value for packet type ret or set.')

    def __repr__(o, kwparams='unit rw nullable'):
        # build placeholder string a=%(a)s, b=%(b)s ...
        # kwparams is used by the subclasses.
        kwparams = ', '.join(['%s=%%(%s)r'%(param, param) for param in kwparams.split(' ')])
        d = o.__dict__.copy()
        d['cls'] = o.__class__.__name__
        return '%(cls)s(0x%(telegram_id)0.8X, %(disp_id)04d, %(disp_name)r'%d+kwparams%d+')'

    def __str__(o):
        if o.disp_id!=0:
            result = u'%d '%o.disp_id + o.disp_name 
            # Python2 compat
            return result if isinstance(result, str) else result.encode('utf8')
        else:
            return '0x%0.8X'%o.telegram_id

    @property
    def _extra_description(o):
        '''additional info for subclasses'''
        return u''
    
    @property
    def short_description(o):
        return u'''{fmrw}{o.disp_id:04d} {o.telegram_id:08X} {o.disp_name}{fmunit}'''.format(
            o=o,
            fmunit=u' [%s]'%o.unit if o.unit else u'',
            fmrw = u'*' if o.rw else u' ',
        )
    
    @property
    def long_description(o):
        return u'''{o.short_description}
    {o.type_description}{fmnullable}. {o._extra_description}'''.format(
        o=o,
        fmnullable=u' or --' if o.nullable else u'',
    )
   
class BsbFieldChoice(BsbField):
    '''choice between several options,
    encoded as int16, choices enumerated starting from 0.
    '''
    type_name = 'choice'
    type_description = u'Choice value'
    
    def __init__(o, telegram_id, disp_id, disp_name, choices, rw=False, *args, **kwargs):
        BsbField.__init__(o, nullable=False, **xo(locals()))
        if not isinstance(choices, dict):
            d = {}
            for n, choice in enumerate(choices):
                if not choice: continue
                d[n] = choice
            o.choices = d
        else:
            o.choices = choices
        o._choices_inv = dict(map(reversed, o.choices.items()))
        
    def __repr__(o):
        return BsbField.__repr__(o, kwparams='choices rw')
        
    def _decode_data(o, rawdata):
        assert len(rawdata)==2
        idx = rawdata[1]
        try:
            return (idx, o.choices[idx])
        except KeyError:
            return (idx, '')
            return u'<Unknown state: %d>'%idx
        
    def _validate_data(o, choice):
        if isinstance(choice, tuple):
            choice = choice[0]
        if isinstance(choice, basestring):
            if choice not in o._choices_inv:
                raise ValidateError('Invalid choice string for field %s: %s'%(o.disp_id, choice))
        else:
            if choice not in o.choices:
                raise ValidateError('Invalid choice index for field %s: %s'%(o.disp_id, choice))
        
    def _encode_data(o, choice, flag):
        '''choice can be given as number or as string.'''
        if choice is None:
            return [flag, 0]
        if isinstance(choice, tuple):
            choice = choice[0]
        if isinstance(choice, basestring):
            try:
                choice = o.choices_inv[choice]
            except KeyError:
                raise EncodeError('Invalid choice string for this field: %s'%choice)
        else:
            try:
                choice = int(choice)
            except (TypeError, ValueError):
                raise EncodeError('Value cannot be cast to int: %r'%choice)
        if choice<0 or choice > 255:
            raise EncodeError('choice value %d out of range 0-255'%choice)
        return [flag, choice]
    
    @property
    def _extra_description(o):
        return u'''Possible values:
        {fmchoices}'''.format(
            fmchoices = u'\n        '.join([
                str(key) + u': ' + o.choices[key]
                for key in sorted(o.choices.keys())
            ]),
        )
        
class BsbFieldInt8(BsbField):
    '''bytesized value. two bytes: <flag> <value>, variable unit
    '''
    type_name = 'int8'
    type_description = u'Integer 8-bit'
    def __init__(o, telegram_id, disp_id, disp_name, unit=u'', tn='', rw=False, nullable=False, min=None, max=None, *args, **kwargs):
        BsbField.__init__(o, **xo(locals()))
        o.min = min or 0
        o.max = max or 255
        
    def __repr__(o):
        return BsbField.__repr__(o, kwparams='unit rw nullable min max')
        
    @property
    def _extra_description(o):
        return u''' Allowed range: {min} ... {max}.'''.format(
            min=o.min,
            max=o.max,
        )
        
    def _decode_data(o, rawdata):
        assert len(rawdata)==2
        return rawdata[1]
        
    def _validate_data(o, value):
        prefix = 'Field %s: Value %r'%(o.disp_id, value)
        if not isinstance(value,int):
            raise ValidateError(prefix +' is not an int.')
        if o.min is not None and value < o.min:
            raise ValidateError(prefix +' is below min value of %d'%o.min)
        if o.max is not None and value > o.max:
            raise ValidateError(prefix +'is above max value of %d'%o.max)
        
    def _encode_data(o, value, flag):
        if value is None:
            return [flag, 0]
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise EncodeError('Value %r cannot be cast to int'%value)
        if value < 0 or value > 255:
            raise EncodeError('Int8 value %r out of range 0-255'%(value,))
        return [flag, value]
        
class BsbFieldInt16(BsbField):
    '''numeric value encoded as <flag> + int16, variable unit.
    optional divisor can be given for fixed-point field (when reading, 
    int value is divided by divisor).'''
    type_name = 'int16'
    type_description = u'Fixed-point 16-bit'
    
    def __init__(o, telegram_id, disp_id, disp_name, unit=u'', tn='', rw=False, nullable=False, divisor=1, min=None, max=None, *args, **kwargs):
        BsbField.__init__(o, **xo(locals()))
        o.divisor = divisor
        o.min = -32768 if min is None else int(min*divisor)
        o.max = 32767 if max is None else int(max*divisor)
        
    @property
    def _extra_description(o):
        return u'''Allowed range: {min} ... {max} in steps of {fmdiv:g}.'''.format(
            min=o.min/o.divisor,
            max=o.max/o.divisor,
            fmdiv=1.0/o.divisor,
        )
        
    def _decode_data(o, rawdata):
        assert len(rawdata)==3
        val = rawdata[1]*0x100 + rawdata[2]
        if val >= 0x8000:
            val-= 0x10000
        return val/o.divisor
    
    def _validate_data(o, value):
        prefix = 'Field %s: Value %r'%(o.disp_id, value)
        try:
            value = int(value*o.divisor)
        except (TypeError, ValueError):
            raise ValidateError(prefix +' cannot be converted to int.')
        if value < o.min:
            raise ValidateError(prefix +' is below min value of %d'%(o.min/o.divisor))
        if value > o.max:
            raise ValidateError(prefix +'is above max value of %d'%(o.max/o.divisor))
    
    def _encode_data(o, value, flag):
        if value is None:
            return [flag, 0, 0]
        try:
            value = int(value*o.divisor)
        except (TypeError, ValueError):
            raise EncodeError('Value cannot be cast to int: %r'%value)
        if value < -0x8000 or value >= 0x8000:
            raise EncodeError('Not a int16 value: %r'%(value,))
        if value<0:
            value += 0x10000
        return [flag, value // 0x100, value & 0xff]

class BsbFieldTemperature(BsbFieldInt16):
    type_name = 'temperature'
    type_description = u'Temperature'
    def __init__(o, telegram_id, disp_id, disp_name, rw=False, nullable=False, min=None, max=None, *args, **kwargs):
        BsbFieldInt16.__init__(o, unit=u'°C', divisor=64.0, **xo(locals()))
        
class BsbFieldInt32(BsbField):
    '''numeric value encoded as <flag> + int32, variable unit.
    optional divisor can be given for fixed-point field (when reading, 
    int value is divided by divisor).'''
    type_name = 'int32'
    type_description = u'Fixed-point 16-bit'
    
    def __init__(o, telegram_id, disp_id, disp_name, unit=u'', tn='', rw=False, nullable=False, divisor=1, min=None, max=None, *args, **kwargs):
        BsbField.__init__(o, **xo(locals()))
        o.divisor = divisor
        o.min = -0x80000000 if min is None else int(min*divisor)
        o.max = 0x7fffffff if max is None else int(max*divisor)
        
    @property
    def _extra_description(o):
        return u'''Allowed range: {min} ... {max} in steps of {fmdiv:g}.'''.format(
            min=o.min/o.divisor,
            max=o.max/o.divisor,
            fmdiv=1.0/o.divisor,
        )
        
    def _decode_data(o, rawdata):
        assert len(rawdata)==5
        val = rawdata[1]*0x1000000 + rawdata[2]*0x10000 + rawdata[3]*0x100 + rawdata[4]
        if val >= 0x80000000:
            val-= 0x100000000
        return val/o.divisor
    
    def _validate_data(o, value):
        prefix = 'Field %s: Value %r'%(o.disp_id, value)
        try:
            value = int(value*o.divisor)
        except (TypeError, ValueError):
            raise ValidateError(prefix +' cannot be converted to int.')
        if value < o.min:
            raise ValidateError(prefix +' is below min value of %d'%(o.min/o.divisor))
        if value > o.max:
            raise ValidateError(prefix +'is above max value of %d'%(o.max/o.divisor))
        raise ValidateError('Field %s: Value encoding for int32-set is not verified on actual hardware yet. Aborting.')
    
    def _encode_data(o, value, flag):
        if value is None:
            return [flag, 0, 0, 0, 0]
        try:
            value = int(value*o.divisor)
        except (TypeError, ValueError):
            raise EncodeError('Value cannot be cast to int: %r'%value)
        if value < -0x80000000 or value >= 0x80000000:
            raise EncodeError('Not a int32 value: %r'%(value,))
        if value<0:
            value += 0x100000000
        return [flag, (value // 0x1000000) & 0xff, (value // 0x10000) & 0xff, (value // 0x100) & 0xff, value & 0xff]
    
class BsbFieldTime(BsbField):
    '''time encoded as <flag> <hour> <minute>.
    '''
    type_name='time'
    type_description = u'Time Value'
    def __init__(o, telegram_id, disp_id, disp_name, rw=False, nullable=False, *args, **kwargs):
        BsbField.__init__(o, **xo(locals()))
        
    @property
    def _extra_description(o):
        return u''
    
    def _decode_data(o, rawdata):
        assert len(rawdata)==3
        return time(rawdata[1], rawdata[2])
    
    def _validate_data(o, data):
        try:
            h, m = data.hour, data.minute
        except AttributeError:
            raise ValidateError('Field %s: value misses hour and/or minute attribute.'%o.disp_id)
        if not isinstance(h, int) or h<0 or h>23:
            raise ValidateError('Field %s: invalid hour %r'%(o.disp_id, h))
        if not isinstance(m, int) or m<0 or m>59:
            raise ValidateError('Field %s: invalid minute %r'%(o.disp_id, m))
        # XXX: original control pad only allows minute divisible by ten. Not constrained here.
    
    def _encode_data(o, val, flag):
        if val is None:
            return [flag, 0, 0]
        try:
            h, m = val.hour, val.minute
        except AttributeError:
            raise EncodeError('Value %r misses hour and/or minute attribute.'%val)
        if not isinstance(h, int) or h<0 or h>255: raise EncodeError('not a byte value: %r'%h)
        if not isinstance(m, int) or m<0 or m>255: raise EncodeError('not a byte value: %r'%m)
        return [flag, h, m]
