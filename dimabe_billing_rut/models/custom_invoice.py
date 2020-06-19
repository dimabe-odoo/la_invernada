from odoo import models, fields, api
import json
import requests
import inspect
from datetime import date


class CustomInvoice(models.Model):
    _name = 'custom.invoice'

    date = fields.Date('Fecha de Emision')

    transmitter = fields.Char('Emisor')

    partner_id = fields.Many2one('res.partner', 'Contacto')

    dte = fields.Many2one('dte.type', 'Tipo de Dte')

    business_name = fields.Char('Razon Social')

    invoice = fields.Char('Folio')

    branch_office = fields.Char('Sucursal')

    exempt = fields.Boolean('Exento')

    net_value = fields.Float('Neto')

    total_value = fields.Float('Total')

    dv = fields.Integer('Dv')

    rut_f = fields.Char('Rut Emisor')

    giro = fields.Char('Giro')

    def get_dte(self):
        company = self.env.user.company_id
        url = self.company_id.dte_url
        rut_company = self.company_id.invoice_rut.replace(".", "").split("-")[0]
        fecha_desde = '2020-01-01'
        fecha_hasta = date.today()
        apidte = '/dte/dte_recibidos/buscar/{}?fecha_desde={}&fecha_hasta={}'.format(rut_company, fecha_desde,
                                                                                     fecha_hasta)
        hash = self.company_id.dte_hash
        auth = requests.auth.HTTPBasicAuth(hash, 'X')
        dtes = requests.get(url + '/api' + apidte, auth=auth)
        data = dtes.json()
        raise models.ValidationError(data)
        for d in data:
            partner_id = self.env['res.partner'].search([('invoice_rut', '=', d.get('rut_f').strip())])
            dte_type = self.env['dte.type'].search([('code', '=', d.get('dte', None))])
            self.env['custom.invoice'].create({
                'date': d.get('fecha', None),
                'transmitter': d.get('emisor', None),
                'partner_id': partner_id.id,
                'dte': dte_type.id,
                'business_name': d.get('razon_social', None),
                'invoice': d.get('folio', None),
                'branch_office': d.get('sucursal', None),
                'exempt': False,
                'net_value': d.get('neto', None),
                'total_value': d.get('total', None),
                'dv': d.get('dv', None),
                'rut_f': d.get('rut_f', None),
                'giro': d.get('giro', None),
            })

    def test(self):
        raise models.ValidationError('Funciona')