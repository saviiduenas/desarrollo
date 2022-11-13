# -*- coding: utf-8 -*-

import time
import math
import re

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    fel_usuario = fields.Char('Usuario feel')
    fel_llave_pre_firma = fields.Char('Llave pre firma feel')
    fel_llave_firma = fields.Char('Llave firma feel')
    feel_frase = fields.Char('Tipo de frase Feel')
    fel_frase_ids = fields.One2many('infilefel.frase','company_id','Frases')
    feel_codigo_exportador = fields.Char('Codigo exportador')
    certificador = fields.Char('Certificador', default="INFILE")
    fel_logo = fields.Binary('Logo fel')
    fel_texto_logo = fields.Char('Texto logo fel')

    # feel_codigo_establecimiento = fields.Char('Codigo de establecimiento')
