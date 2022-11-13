# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    fel_tipo_dte = fields.Selection([
            ('FACT', 'Factura'),
            ('FCAM', 'Factura cambiaria'),
            ('FPEQ', 'Factura pequeño contribuyente'),
            ('FCAP', 'Factura cambiaria pequeño contribuyente'),
            ('FESP', 'Factura especial'),
            ('NABN','Nota de abono'),
            ('RDON','Recibo de doanción'),
            ('RECI','Recibo'),
            ('NDEB','Nota de Débito'),
            ('NCRE','Nota de Crédito'),
            ('FACA','Factura Contribuyente Agropecuario'),
            ('FCCA','Factura Cambiaria Contribuyente Agropecuario'),
            ('FAPE','Factura Pequeño contribuyente Regimen Elctrónico'),
            ('FCPE','Factura Cambiaria Pequeño contribuyente Regimen Elctrónico'),
            ('FAAE','Factura Contribuyente Agropecuario Régimen Electrónico especial'),
            ('FCAE','Factura Cambiaria Contribuyente Agropecuario Régimen Electrónico especial'),
        ],string="Tipo DTE",
        help="Tipo de DTE (documento para feel)")
    fel_codigo_establecimiento = fields.Char('Codigo de establecimiento')
    fel_nombre_comercial = fields.Char('Nombre comercial')
    direccion_id = fields.Many2one('res.partner','Dirección')
