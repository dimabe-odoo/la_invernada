from odoo import models, fields, api


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    show_in_book = fields.Boolean('Aparece en el libro de remuneraciones')
