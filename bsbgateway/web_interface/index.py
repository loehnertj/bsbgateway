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
from .templates import tpl
from .field import Field

class Index(object):
    url = r''
    def GET(o):
        dash_fields = web.ctx.dash_fields
        dash_breaks = web.ctx.dash_breaks
        return tpl.base(
            tpl.index(
                dash_fields,
                web.ctx.bsb.groups,
                o.render_field,
                dash_breaks,
            )
        )

    def render_field(o, field):
        return Field().dashwidget(field)