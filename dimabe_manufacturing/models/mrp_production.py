from odoo import fields, models, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    stock_lots = fields.Many2one("stock.production.lot")

    stock_lots_id = fields.One2many(
        related="stock_lots.stock_production_lot_serial_ids")

    @api.onchange('product_id')
    def _get_data_lot(self):
        lots = fields.Many2one("stock.production.lot")
        for item in lots:
            if lots.product_qty >= 0 and lots.product_id == self.product_id:
                models._logger.error(
                    "qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq {}".format(item))
                models._logger.error(
                    "qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq {}".format(lots))

    @api.multi
    def calculate_done(self):
        for item in self:
            for line_id in item.finished_move_line_ids:
                line_id.qty_done = line_id.lot_id.total_serial

    @api.multi
    def button_mark_done(self):
        self.calculate_done()
        return super(MrpProduction, self).button_mark_done()
