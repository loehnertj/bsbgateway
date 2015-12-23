from Queue import Queue
import logging
log = lambda: logging.getLogger(__name__)
import web
from event_sources import EventSource
from index import Index
from field import Field
from group import Group

_HANDLERS = [
    Index,
    Field,
    Group,
]

def add_to_ctx(obj, key):
    '''makes a processor that attaches the given obj to web.ctx as property "key".'''
    def processor(handler):
        setattr(web.ctx, key, obj)
        return handler()
    return processor

def print_handlers(urls):
    s = ["URL Mapping:"]
    for url, cls in zip(urls[::2], urls[1::2]):
        s.append(str(url))
        s.append("  --> "+cls.__module__ + "." + cls.__name__)
        s.append('')
    log().info('\n    '.join(s))

class WebInterface(EventSource):
    def __init__(o, name='web'):
        o.name = name
        o.stoppable = False
        
    def run(o, putevent):
        urls = []
        for cls in _HANDLERS:
            urls.append('/' + cls.url)
            urls.append(cls)
            
        print_handlers(urls)
        
        app = web.application(urls)
        app.add_processor(add_to_ctx(Web2Broetje(o.name, putevent), 'broetje'))
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", 8081)) 

class Web2Broetje(object):
    '''provides the connection from web to backend.'''
    def __init__(o, evname, putevent):
        o.evname = evname
        o.putevent = putevent
        
    def get(o, disp_id):
        rq = Queue()
        o.putevent(o.evname, [rq, 'get', disp_id])
        return rq
        
    def set(o, disp_id, value):
        # FIXME: who decodes the value (str -> val)?
        rq = Queue()
        o.putevent(o.evname, [rq, 'set', disp_id, value])
        return rq
        