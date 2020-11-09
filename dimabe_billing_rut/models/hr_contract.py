from odoo import fields, models, api


class ModelName (models.Model):
    _inherit = 'hr.contract'

    compensation_saving_id = fields.Many2one('hr.ccaf','Caja de Compensasion')

    saving_value = fields.Float('Valor de Ahorro')

    