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