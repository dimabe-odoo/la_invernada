from odoo import fields, models, api
from .rut_helper import prepare_rut


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_rut = fields.Char(
        'Rut Facturación'
    )

    economic_activities = fields.Many2many('custom.economic.activity', string='Actividades de la empresa')
    
    dte_url = fields.Char(string='URL portal de Facturacion',
                          help='',
                          required=True,
                          default='https://services.dimabe.cl/api/dte/emite')
    ticket_url = fields.Char(string='URL Validacion de Boletas',
                          help='',
                          required=True,
                          default='http://dte.xdte.cl/boletas')
    resolution_date = fields.Date(string='Fecha Resolución',
                         help='Fecha de Resolución entregada por el SII',
                         required=True,
                         default='2014-08-22')
    resolution_number = fields.Integer(string='Numero Resolución',
                                   help='Número de Resolución entregada por el SII',
                                   required=True,
                                   default='80')
                                   
    dte_hash = fields.Char(string='ApiKey Cliente',
                                    help='ApiKey Cliente Facturador Electrónico',
                                    required=True,
                                    default='')
    dte_customer_code = fields.Char(string='Código Cliente',
                                    help='Código Cliente Facturador Electrónico',
                                    required=True,
                                    default='')
    


    add_to_sale_book = fields.Boolean()

    @api.model
    def create(self, values_list):
        prepare_rut(values_list)
        return super(ResCompany, self).create(values_list)

    @api.multi
    def write(self, values):
        prepare_rut(values)
        return super(ResCompany, self).write(values)
