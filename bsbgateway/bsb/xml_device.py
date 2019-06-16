# coding: utf8
import os
import itertools as it
from collections import namedtuple
from .bsb_field import BsbField, BsbFieldChoice, BsbFieldInt8, BsbFieldInt16, BsbFieldInt32, BsbFieldTemperature, BsbFieldTime

#import untangle
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class XmlDeviceError(ValueError):
    '''raised when reading the xml file fails'''
    pass

Group = namedtuple('Group', 'disp_id name fields')

class AttributeDict(dict): 
    def __getattr__(self, key):
        return self.get(key, '')
    
    
class XmlDevice(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("File does not exist: '%s'"%filename)
        tree = ET.parse(filename)
        self.groups = self._read_groups(tree)
        
        _all = it.chain(*[g.fields for g in self.groups])
        self.fields = {f.disp_id: f for f in _all}
        self.fields_by_telegram_id = {f.telegram_id: f for f in self.fields.itervalues()}
        
    def _read_groups(self, tree):
        groups = []
        for category_elem in tree.iter('category'):
            category = category_elem.attrib
            fields = [self._read_field(cmddef_elem) for cmddef_elem in category_elem.iter('cmdDef')]
            disp_id = 0
            try:
                disp_id = int(category.get('name', u'0')[:4])
            except ValueError:
                pass
            groups.append(Group(disp_id, unicode(category.get('name', u'?')), fields))
        return groups
    
    def _read_field(self, cmddef_elem):
        cmd = AttributeDict(cmddef_elem.attrib)
        t = cmd.payloadType.lower()
        kwargs = {}
        
        fieldcls = {
            '': BsbField,
            'unknown': BsbField,
            'choice': BsbFieldChoice,
            'int08': BsbFieldInt8,
            'int16': BsbFieldInt16,
            'int32': BsbFieldInt32,
            # still unsupported :-(
            'datetime': BsbField,
            'schedule': BsbField,
            'string': BsbField,
            'summerwinter': BsbField,
            'vacation': BsbField,
        }.get(t, None)
        if not fieldcls:
            raise XmlDeviceError('Field %s has unsupported payloadType %s'%(cmd.progNr, cmd.payloadType))
        
        ll = {'choice':2, 'int08':2, 'int16':3, 'int32':5}.get(t, 0)
        if ll and int(cmd.length) != ll:
            raise XmlDeviceError('Field %s has wrong length for its payload type')
        try:
            if t in ('choice',):
                kwargs['rw'] = (cmd.writeable =='true')
                kwargs['choices'] = {
                    int(ch.attrib['val']): unicode(ch.attrib['text'])
                    for ch in cmddef_elem.iter('choice')
                }
                
            if t in ('int08', 'int16', 'int32'):
                kwargs['rw'] = (cmd.writeable=='true')
                kwargs['nullable'] = (cmd.nullable=='true')
                if cmd.unit == u'°C' and cmd.scale=='64':
                    fieldcls = BsbFieldTemperature
                else:
                    kwargs['unit'] = unicode(cmd.unit)
                    if cmd.scale and cmd.scale != 'Unknown':
                        kwargs['divisor'] = float(cmd.scale)
                    else:
                        kwargs['divisor'] = 1.0
                # FIXME: durch Divisor teilen??
                if cmd.min and cmd.min != 'Unknown':
                    kwargs['min'] = _tfloat(cmd.min)
                if cmd.max and cmd.max != 'Unknown':
                    kwargs['max'] = _tfloat(cmd.max)
        except ValueError as e:
            raise XmlDeviceError('Field %s contains an illegal attribute value: %s'%(cmd.progNr, str(e)))
        
        # TODO: default, scale in Bsb-Fields hinterlegen
        
        disp_id = int(cmd.progNr)
        telegram_id = int(cmd.cmdCode, 16)
                            
        return fieldcls(telegram_id, disp_id, unicode(cmd.name), **kwargs)
    
    def __str__(self):
        s = []
        for group in self.groups:
            s.append(u'%04d %s'%(group.disp_id, group.name))
            for field in group.fields:
                s.append(u'   %s'%field.long_description)
        return u'\n'.join(s) 
    
def _tfloat(s):
    if ':' in s:
        # time value aa:bb or aa:bb:cc
        # return value in units of the last part (e.g. hh:mm in minutes, mm:ss in seconds)
        parts = [int(p) for p in s.split(':')]
        return reduce(lambda x, y: 60*x+y, parts)
    x = float(s)
    if int(x)==x:
        return int(x)
    else:
        return x
