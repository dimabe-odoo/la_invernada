from odoo import models, fields, api

class CustomOrdersToInvoice(models.Model):
    _name = 'custom.orders.to.invoice'

    stock_picking_id = fields.Integer(string="Despacho Id", required=True)

    stock_picking_name = fields.Char(string="Despacho", required=True)

    order_id = fields.Integer(string="Pedido Id", required=True)

    order_name = fields.Char(string="Pedido", required=True)

    product_id = fields.Integer(string="Producto Id", required=True)

    product_name = fields.Char(string="Producto", required=True)

    #quantity = fields.Float(string="Cantidad")

    quantity_to_invoice = fields.Char(string="Cantidad por Facturar", required=True)

    invoice_id = fields.Many2one(
        'account.invoice',
        index=True,
        copy=False,
        string="Pedido"
    )