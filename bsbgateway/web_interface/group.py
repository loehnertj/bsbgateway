import web
from bsb.bsb_fields import groups
from templates import tpl
from field import Field

class Group(object):
    url = r'group-([0-9]+)'
    
    def GET(o, disp_id):
        disp_id = int(disp_id)
        g = [g for g in groups if g.disp_id == disp_id]
        if len(g)!=1:
            raise web.notfound()
        group = g[0]
        return tpl.base(tpl.group(group, o.render_field), '#'+group.name)
    
    def render_field(o, field):
        return Field().fragment(field)