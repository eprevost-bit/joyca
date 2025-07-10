# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: MAyana KP (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import hashlib
import odoo
from odoo import http
from odoo.tools import pycompat
from odoo.tools.translate import _
from odoo.http import request
from odoo.addons.web.controllers.home import Home as WebHome


# No necesitas _get_login_redirect_url ni SIGN_UP_REQUEST_PARAMS aquí
# porque el controlador de Odoo ya los maneja.

import hashlib
import odoo
from odoo import http
from odoo.tools import pycompat
from odoo.tools.translate import _
from odoo.http import request
from odoo.addons.web.controllers.home import Home as WebHome


class Home(WebHome):
    @http.route(route='/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        # 1. Ejecutar la lógica de login original de Odoo.
        response = super(Home, self).web_login(redirect=redirect, **kw)

        # 2. Comprobar si la respuesta es una redirección por su código de estado (3xx).
        #    ESTA ES LA LÍNEA CORREGIDA.
        if 300 <= response.status_code < 400:
            return response

        # 3. Si no es una redirección, continuamos con la lógica personalizada.
        values = response.qcontext

        # 4. Añadimos NUESTRA lógica para estilos y fondos.
        conf_param = request.env['ir.config_parameter'].sudo()
        orientation = conf_param.get_param('web_login_styles.orientation')
        image = conf_param.get_param('web_login_styles.image')
        url = conf_param.get_param('web_login_styles.url')
        background_type = conf_param.get_param('web_login_styles.background')

        if background_type == 'color':
            values['bg'] = ''
            values['color'] = conf_param.sudo().get_param('web_login_styles.color')
        elif background_type == 'image':
            attachment = request.env['ir.attachment'].sudo().search([('name', '=', 'web_login_background')], limit=1)
            if image and (not attachment or attachment.checksum != image):
                if not attachment:
                    attachment = request.env['ir.attachment'].sudo().create(
                        {'name': 'web_login_background', 'public': True})
                attachment.write({'datas': image})

            if attachment:
                values['bg_img'] = f"/web/image/{attachment.id}?field=datas"

        elif background_type == 'url' and url:
            values['bg_img'] = url

        # 5. Renderizamos la plantilla personalizada correcta.
        if orientation == 'right':
            return request.render('web_login_styles.login_template_right', values)
        elif orientation == 'left':
            return request.render('web_login_styles.login_template_left', values)
        elif orientation == 'middle':
            return request.render('web_login_styles.login_template_middle', values)

        # Si no hay ninguna orientación personalizada, devolvemos la respuesta original de Odoo.
        return response
