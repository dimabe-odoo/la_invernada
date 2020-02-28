from odoo import fields, models, api


class DriedOven(models.Model):
    _name = 'dried.oven'
    _description = 'horno de secado'

    name = fields.Char('Horno')

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.name = str.upper(self.name)

    @api.model
    def create(self, vals_list):
        if 'name' in vals_list and not vals_list['name'] is False:
            vals_list['name'] = str.upper(vals_list['name'])

        return super(DriedOven, self).create(vals_list)

