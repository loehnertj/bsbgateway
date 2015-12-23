import web
from templates import tpl
from bsb.bsb_fields import groups

class Index(object):
    url = r''
    def GET(o):
        return tpl.base(tpl.index(groups))