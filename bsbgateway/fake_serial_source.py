import logging
log = lambda: logging.getLogger(__name__)
import datetime
import time
from Queue import Queue

from event_sources import EventSource

class SerialSource(EventSource):
    
    def __init__(o, name, *whatever, **more_stuff):
        o.name = name
        o.stoppable = True
        o.rdqueue = Queue()
        o.state = {}

    def run(o, putevent_func):
        log().warning('WARNING: USING FAKE!! SERIAL PORT')
        while not o._stopflag:
            data = o.rdqueue.get(1)
            if not data: continue
            time.sleep(0.1)
            log().debug('RETURN: [%s]'%data.encode('hex'))
            putevent_func(o.name, (time.time(), data))

    def write(o, data):
        log().debug('FAKE write: [%s]'%(data.encode('hex')))
        from bsb.bsb_telegram import BsbTelegram
        t = BsbTelegram.deserialize(data)[0]
        
        # remember set value for session
        if t.packettype == 'set':
            log().debug('cached value of %r'%(t.data,))
            o.state[t.field.disp_id] = t.data
            
        t.src, t.dst = t.dst, t.src
        t.packettype = {'set':'ack', 'get':'ret'}[t.packettype]
        
        # for GET, return current state if set, else default value dep. on field type.
        if t.packettype == 'ret':
            try:
                t.data = o.state[t.field.disp_id]
            except KeyError:
                t.data = {
                    'choice': 1,
                    'time': datetime.time(13,37),
                }.get(t.field.type_name, 42)
        rdata = t.serialize(validate=False)
        o.rdqueue.put(rdata)
