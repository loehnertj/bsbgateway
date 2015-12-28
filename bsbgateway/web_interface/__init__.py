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

from Queue import Queue
import logging
log = lambda: logging.getLogger(__name__)
from datetime import datetime
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
    def __init__(o, name, device, port=8080):
        o.name = name
        o.device = device
        o.port = port
        o.stoppable = False
        o.server = None
        
    def run(o, putevent):
        urls = []
        for cls in _HANDLERS:
            urls.append('/' + cls.url)
            urls.append(cls)
            
        print_handlers(urls)
        
        app = web.application(urls)
        app.add_processor(add_to_ctx(Web2Bsb(o.name, o.device, putevent), 'bsb'))
        #web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", o.port)) 
        o.server = o.startserver(app.wsgifunc(), o.port)
        
    def startserver(o, func, port):
        from web.httpserver import WSGIServer, StaticMiddleware
        func = StaticMiddleware(func)
        func = MyLogMiddleware(func)
    
        o.server = WSGIServer(("0.0.0.0", port), func)

        log().info("Web interface listening on http://0.0.0.0:%d/" % port)

        o.server.start()
        
    def stop(o):
        if o.server:
            o.server.stop()
            o.server = None

class Web2Bsb(object):
    '''provides the connection from web to backend.'''
    def __init__(o, evname, device, putevent):
        o.evname = evname
        o.device = device
        o.putevent = putevent
        
    @property
    def fields(o):
        return o.device.fields
    
    @property
    def groups(o):
        return o.device.groups
        
    def get(o, disp_id):
        rq = Queue()
        o.putevent(o.evname, [rq, 'get', disp_id])
        return rq
        
    def set(o, disp_id, value):
        # FIXME: who decodes the value (str -> val)?
        rq = Queue()
        o.putevent(o.evname, [rq, 'set', disp_id, value])
        return rq
        
        
# Ripped from web.httpserver, and somewhat modified.
# LICENSE NOTICE: web.py is Public Domain. So this class is exempt from the GPL claim.
class MyLogMiddleware:
    """WSGI middleware for logging the status."""
    def __init__(self, app):
        self.app = app
        self.template = '{host}: {method} {req} - {status}'
        
    def __call__(self, environ, start_response):
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ)
            return out

        return self.app(environ, xstart_response)
             
    def log(self, status, environ):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_')
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                          environ.get('REMOTE_PORT','-'))

        time = datetime.now().isoformat()

        msg = self.template.format(**locals())
        log().info(msg)
