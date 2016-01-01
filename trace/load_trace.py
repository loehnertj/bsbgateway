'''
Load trace files as numpy arrays.
'''
import logging
log = lambda: logging.getLogger(__name__)
import numpy as np
from datetime import time, datetime


converters = {
# Legacy data types
    'none': lambda _: None,
    'string': lambda x: x,
    'hex': lambda x: int(x, 16), 
    'float': lambda x: float(x),
    
# New field types
    '': lambda x: int(x, 16),
    'choice': int,
    'int8': int,
    'temperature': float,
    'int16': float,
    'time': lambda x: time(*map(int, x.split(':')))
}


class Trace(object):
    '''loads and decodes a trace file's content.
    
    Trace(filename, start=None, end=None) -> Trace object
    :param filename: Path of the file to be loaded.
    :param start: Optional, unix timestamp of where to start reading (inclusive).
    :param end: Optional, unix timestamp of where to stop reading (inclusive).
    :returns: Trace object having the file's data and metadata as attributes.
    
    Trace object attributes:
    
    * dtype: the value datatype as given in the file.
    * disp_id: The field's disp_id as given in the file.
    * fieldname: Field name as given in the file; unicode object
    * index: Array of timestamps (unix timestamp)
    * data: Array of values
    
    If the meta fields appear multiple times (typically after restart),
    the last found value is remembered.
    
    Index and data array have the same dimension. If start/end are given
    to the constructor, Index is restricted to this interval.
    
    Index: datetime.datetime objects
    
    The data array's type depends on the field dtype:
        * choice, int8 -> int
        * int16, temperature -> float
        * time -> datetime.time
        * (unknown) -> int (big-endian interpretation of value bytes)
    
    '''
    def __init__(o, filename, start=None, end=None):
        fh = open(filename, 'r')
        index = []
        data = []
        fieldname = ''
        disp_id = 0
        curtime = 0
        interval = 1
        converter = converters['none']
        dtype = 'none'
        
        for line in fh:
            if line == '\n': continue
            if line.startswith(':'):
                # Metadata line. Compare with the values found so far.
                attrname, _, attrvalue = line[:-1].partition(' ')
                if attrname == ':disp_id':
                    disp_id = int(attrvalue)
                elif attrname == ':fieldname':
                    fieldname = attrvalue.decode('utf8')
                elif attrname == ':interval':
                    interval = int(attrvalue)
                elif attrname == ':time':
                    curtime = int(attrvalue)
                elif attrname == ':dtype':
                    converter = converters[attrvalue]
                    dtype = attrvalue
                    
            elif line.replace('~','') =='\n':
                # repeat value only
                for n in xrange(len(line)-1):
                    if curtime >= (start or curtime) and curtime <= (end or curtime):
                        index.append(datetime.fromtimestamp(curtime))
                        data.append(data[-1])
                    curtime += interval
            else:
                # normal value
                val = line[:-1].replace('~', '')
                if (val=='--'):
                    val=None
                else:
                    try:
                        # Try to convert the value, which is the line excluding newline and all repeat markers.
                        val = converter(val)
                    except:
                        log.exception('error converting value %r in %s'%(val, filename))
                        raise
                for n in xrange(line.count('~') + 1):
                    # Append the value and the given number of repetitions.
                    if curtime >= (start or curtime) and curtime <= (end or curtime):
                        data.append(val)
                        index.append(datetime.fromtimestamp(curtime))
                    curtime += interval
        o.disp_id = disp_id
        o.fieldname = fieldname
        o.dtype = dtype
        o.data = np.array(data)
        o.index = np.array(index)