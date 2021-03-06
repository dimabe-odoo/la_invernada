from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
import math


class StockProductionLotSerial(models.Model):
    _inherit = 'stock.production.lot.serial'

    _sql_constraints = [
        ('serial_uniq', 'UNIQUE(serial_number)', 'la serie ya se encuentra en el sistema.')
    ]

    production_id = fields.Many2one(
        'mrp.production',
        'Salida'
    )

    producer_id = fields.Many2one(
        'res.partner',
        'Productor'
    )

    product_variety = fields.Char(
        'Variedad',
        related='stock_production_lot_id.product_variety'
        , store=True
    )

    product_id = fields.Many2one(
        'product.product',
        related='stock_production_lot_id.product_id',
        string='Producto'
    )

    belongs_to_prd_lot = fields.Boolean(
        'pertenece a lote productivo',
        related='stock_production_lot_id.is_prd_lot'
    )

    reserved_to_production_id = fields.Many2one(
        'mrp.production',
        'Entrada',
        nullable=True
    )

    consumed_in_production_id = fields.Many2one(
        'mrp.production',
        'Consumida en la produccion',
        nullable=True
    )

    stock_product_id = fields.Many2one(
        'product.product',
        related='stock_production_lot_id.product_id',
        string='Producto'
    )

    reserved_to_stock_picking_id = fields.Many2one(
        'stock.picking',
        'Para Picking',
        nullable=True
    )

    validate_to_stock_picking_id = fields.Many2one(
        'stock.picking',
        'Validado',
        nullable=True
    )

    is_dried_serial = fields.Boolean(
        'Es Serie Secada',
        related='stock_production_lot_id.is_dried_lot'
    )

    consumed = fields.Boolean('Consumido')

    confirmed_serial = fields.Char('Confimación de Serie')

    pallet_id = fields.Many2one(
        'manufacturing.pallet',
        'Pallet'
    )

    packaging_date = fields.Date(
        'Fecha Producción',
        default=fields.Date.today()
    )

    best_before_date = fields.Date(
        'Consumir antes de',
        compute='_compute_best_before_date'
    )

    harvest = fields.Integer(
        'Año de Cosecha',
        compute='_compute_harvest'
    )

    harvest_filter = fields.Integer(
        'Año de Cosecha',
        compute='_compute_harvest_filter',
        store=True
    )

    canning_id = fields.Many2one(
        'product.product',
        'Envase',
        inverse='_inverse_gross_weight'
    )

    gross_weight = fields.Float(
        'Peso Bruto',
        digits=dp.get_precision('Product Unit of Measure'),
        inverse='_inverse_gross_weight'
    )

    label_durability_id = fields.Many2one(
        'label.durability',
        'Dirabilidad Etiqueta'
    )

    label_percent = fields.Float(
        '% Peso Etiqueta',
        digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_label_percent'
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        'Lista de Materiales',
        related='production_id.bom_id'
    )

    movement = fields.Char('Movimiento', compute='_compute_movement')

    in_weight = fields.Float('Kilos Ingresado', compute='_compute_in_weight')

    produce_weight = fields.Float('Kilos Producidos', compute='_compute_produce_weight')

    pallet_name = fields.Char('Folio Pallet', compute='_compute_pallet_name')

    sale_order_id = fields.Many2one('sale.order', 'N° Pedido', compute='_compute_sale_order_id', store=True)

    work_order_id = fields.Many2one('mrp.workorder', 'Order Fabricacion', compute='_compute_workorder_id')

    production_id_to_view = fields.Many2one('mrp.production', 'Order de Fabricacion',
                                            compute='_compute_production_id_to_view', store=True)
    workcenter_id = fields.Many2one('mrp.workcenter', related="work_order_id.workcenter_id")

    @api.depends('production_id', 'reserved_to_production_id')
    @api.multi
    def _compute_production_id_to_view(self):
        for item in self:
            if item.reserved_to_production_id:
                item.production_id_to_view = item.reserved_to_production_id
            elif item.production_id:
                item.production_id_to_view = item.production_id
            else:
                item.production_id_to_view = None

    @api.multi
    def _compute_workorder_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.work_order_id = self.env['mrp.workorder'].search(
                    [('production_id', '=', item.reserved_to_production_id.id)])
            elif item.production_id:
                item.work_order_id = self.env['mrp.workorder'].search(
                    [('production_id', '=', item.production_id.id)])
            else:
                item.work_order_id = None

    @api.depends('production_id', 'reserved_to_production_id')
    @api.multi
    def _compute_sale_order_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.sale_order_id = item.reserved_to_production_id.sale_order_id
            elif item.production_id:
                item.sale_order_id = item.production_id.sale_order_id
            else:
                item.sale_order_id = None

    @api.multi
    def _compute_pallet_name(self):
        for item in self:
            if item.stock_production_lot_id.product_id.is_standard_weight:
                if item.pallet_id:
                    item.pallet_name = item.pallet_id.name
                else:
                    item.pallet_name = 'Sin Pallet'

    @api.multi
    def _compute_produce_weight(self):
        for item in self:
            if item.production_id:
                item.produce_weight = item.real_weight
                item.in_weight = 0.0
            else:
                item.produce_weight = 0.0

    @api.multi
    def _compute_in_weight(self):
        for item in self:
            if item.reserved_to_production_id:
                item.in_weight = item.real_weight
                item.produce_weight = 0.0
            else:
                item.in_weight = 0.0
                
    @api.multi
    def undo_consumed(self):
        for item in self:
            item.write({
                'reserved_to_production_id': None,
                'consumed':False
            })
            item.stock_production_lot_id.write({
                'available_kg': sum(item.stock_production_lot_id.filtered(lambda a: not a.consumed).mapped('real_weight'))
            })

    @api.depends('reserved_to_production_id', 'production_id')
    @api.multi
    def _compute_process_id(self):
        for item in self:
            if item.reserved_to_production_id:
                item.process_id = item.reserved_to_production_id.routing_id.name
            elif item.production_id:
                item.process_id = item.production_id.routing_id.name
            else:
                item.process_id = None

    @api.depends('reserved_to_production_id', 'production_id')
    @api.multi
    def _compute_movement(self):
        for item in self:
            if item.reserved_to_production_id and not item.production_id:
                item.movement = 'ENTRADA'
            elif item.production_id and not item.reserved_to_production_id:
                item.movement = 'SALIDA'
            else:
                item.movement = 'NO DEFINIDO'

    @api.multi
    def _inverse_real_weight(self):
        for item in self:
            item.real_weight = item.display_weight
            if not item.is_dried_serial:
                canning_weight = item.canning_id.weight
                if not canning_weight:
                    canning_weight = sum(item.get_possible_canning_id().mapped('weight'))
                item.gross_weight = item.display_weight + canning_weight

    def _inverse_gross_weight(self):
        if self.is_dried_serial:
            gross_weight_without_canning = self.gross_weight - self.canning_id.weight
            self.display_weight = gross_weight_without_canning - (gross_weight_without_canning * self.label_percent)

    @api.multi
    def _compute_label_percent(self):
        for item in self:
            settings_percent = float(self.env['ir.config_parameter'].sudo().get_param(
                'dimabe_manufacturing.label_percent_subtract'
            ))

            if settings_percent:
                item.label_percent = settings_percent / 100

    @api.multi
    def _compute_harvest(self):
        for item in self:
            item.harvest = item.packaging_date.year

    @api.multi
    @api.depends('packaging_date')
    def _compute_harvest_filter(self):
        for item in self:
            item.harvest_filter = item.packaging_date.year

    @api.multi
    def _compute_best_before_date(self):
        for item in self:
            months = item.label_durability_id.month_qty
            item.best_before_date = item.packaging_date + relativedelta(months=months)

    @api.model
    def create(self, values_list):
        res = super(StockProductionLotSerial, self).create(values_list)

        if res.display_weight == 0 and res.gross_weight == 0:
            raise models.ValidationError('debe agregar un peso a la serie')

        stock_move_line = self.env['stock.move.line'].search([
            ('lot_id', '=', res.stock_production_lot_id.id),
            ('lot_id.is_prd_lot', '=', True)
        ])
        production = None
        if stock_move_line.mapped('move_id.production_id'):
            production = stock_move_line.mapped('move_id.production_id')[0]
            res.producer_id = res.stock_production_lot_id.producer_id.id
        else:
            work_order = self.env['mrp.workorder'].search([
                ('final_lot_id', '!=', False),
                ('final_lot_id', '=', res.stock_production_lot_id.id)
            ])

            res.producer_id = res.stock_production_lot_id.producer_id.id

            if work_order.production_id:
                production = work_order.production_id[0]

        if production:
            res.production_id = production.id
            res.reserve_to_stock_picking_id = production.stock_picking_id.id

        res.label_durability_id = res.stock_production_lot_id.label_durability_id

        if res.bom_id:
            if res.bom_id.product_id != res.product_id:
                res.gross_weight = res.display_weight
                return res
            res.set_bom_canning()
            if res.canning_id:
                res.gross_weight = res.display_weight + res.canning_id.weight
            else:
                res.gross_weight = res.display_weight + sum(res.get_possible_canning_id().mapped('weight'))
        return res

    @api.model
    def set_bom_canning(self):
        canning_id = self.get_possible_canning_id()
        if len(canning_id) == 1:
            self.canning_id = canning_id[0]

    @api.model
    def get_possible_canning_id(self):
        return self.bom_id.bom_line_ids.filtered(
            lambda a: 'envases' in str.lower(a.product_id.categ_id.name) or
                      'embalaje' in str.lower(a.product_id.categ_id.name)
                      or (
                              a.product_id.categ_id.parent_id and (
                              'envases' in str.lower(a.product_id.categ_id.parent_id.name) or
                              'embalaje' in str.lower(a.product_id.categ_id.parent_id.name))
                      )
        ).mapped('product_id')

    @api.multi
    def write(self, vals):
        res = super(StockProductionLotSerial, self).write(vals)
        for item in self:
            if item.display_weight == 0 and item.gross_weight == 0:
                raise models.ValidationError('debe agregar un peso a la serie')
            if not item.canning_id and item.bom_id:
                item.set_bom_canning()
        return res

    @api.model
    def unlink(self):
        if self.consumed:
            raise models.ValidationError(
                'este código {} ya fue consumido, no puede ser eliminado'.format(
                    self.serial_number
                )

            )
        group = self.env['res.groups'].search([('name', '=', 'Limpiar')])
        user_logon = self.env.user
        if user_logon not in group.users:
            raise models.ValidationError("Opcion no disponible con sus permisos de usuario")
        return super(StockProductionLotSerial, self).unlink()

    @api.multi
    def delete(self):
        if self.stock_production_lot_id.serial_without_pallet_ids:
            for item in self.stock_production_lot_id.serial_without_pallet_ids:
                if item.id == self.id:
                    item.unlink()

    @api.multi
    def print_serial_label(self):
        if 'producer_id' in self.env.context:
            for item in self:
                item.producer_id = self.env.context['producer_id']

        return self.env.ref(
            'dimabe_manufacturing.action_stock_production_lot_serial_label_report'
        ).report_action(self)

    @api.multi
    def get_full_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return base_url

    @api.multi
    def reserve_picking(self):
        models._logger.error('linea {330} reserve picking')
        if 'dispatch_id' in self.env.context:
            stock_picking_id = self.env.context['dispatch_id']
            stock_picking = self.env['stock.picking'].search([('id', '=', stock_picking_id)])
            models._logger.error(stock_picking)
            if not stock_picking:
                raise models.ValidationError('No se encontró el picking al que reservar el stock')

            for item in self:
                if item.consumed:
                    raise models.ValidationError('Esta serie fue consumida')
                item.update({
                    'reserved_to_stock_picking_id': stock_picking.id
                })
                models._logger.error(item.reserved_to_stock_picking_id)
                stock_move = item.reserved_to_stock_picking_id.move_lines.filtered(
                    lambda a: a.product_id == item.stock_production_lot_id.product_id
                )
                models._logger.error(stock_move)
                stock_quant = item.stock_production_lot_id.get_stock_quant()
                models._logger.error(stock_quant)
                if not stock_quant:
                    raise models.ValidationError('El lote {} aún se encuentra en proceso.'.format(
                        item.stock_production_lot_id.name
                    ))

                if not stock_move:
                    move_line = self.env['stock.move.line'].create({
                        'product_id': item.stock_production_lot_id.product_id.id,
                        'lot_id': item.stock_production_lot_id.id,
                        'qty_done': item.display_weight,
                        'product_uom_id': stock_move.product_uom.id,
                        'location_id': stock_quant.location_id.id,
                        # 'qty_done': item.display_weight,
                        'location_dest_id': stock_picking.partner_id.property_stock_customer.id
                    })

                    stock_move.sudo().update({
                        'move_line_ids': [
                            (4, move_line.id)
                        ]
                    })

                    item.reserved_to_stock_picking_id.update({
                        'move_line_ids': [
                            (4, move_line.id)
                        ]
                    })

                    if stock_quant.total_reserved:
                        stock_quant.sudo().update({
                            'reserved_quantity': stock_quant.total_reserved
                        })
                    else:
                        stock_quant.sudo().update({
                            'reserved_quantity': sum(item.lot_id.stock_production_lot_serial_ids.filtered(
                                lambda a: (a.reserved_to_production_id and a.reserved_to_production_id.state not in [
                                    'done', 'cancel'])
                                          or (a.reserved_to_stock_picking_id and
                                              a.reserved_to_stock_picking_id.state not in ['done', 'cancel']
                                              )
                            ).mapped('display_weight'))
                        })


                else:
                    move_line = stock_move.move_line_ids.filtered(
                        lambda
                            a: a.product_id.id == item.stock_production_lot_id.product_id.id
                    )
                    if not move_line:
                        move_line = self.env['stock.move.line'].create({
                            'product_id': item.stock_production_lot_id.product_id.id,
                            'lot_id': item.stock_production_lot_id.id,
                            'qty_done': item.display_weight,
                            'product_uom_id': stock_move.product_uom.id,
                            'location_id': stock_quant.location_id.id,
                            # 'qty_done': item.display_weight,
                            'location_dest_id': stock_picking.partner_id.property_stock_customer.id
                        })

                        stock_move.sudo().update({
                            'move_line_ids': [
                                (4, move_line.id)
                            ]
                        })

                        item.reserved_to_stock_picking_id.update({
                            'move_line_ids': [
                                (4, move_line.id)
                            ]
                        })
                    else:
                        picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                            lambda a: a.id == move_line.id
                        )
                        models._logger.error(picking_move_line)
                        stock_quant = item.stock_production_lot_id.get_stock_quant()
                        models._logger.error(stock_quant)
                        item.update({
                            'reserved_to_stock_picking_id': stock_picking_id
                        })

                        for ml in move_line:
                            product_uom_qty = ml.product_uom_qty
                            if ml.qty_done > 0:
                                raise models.ValidationError('este producto ya ha sido validado')

                            ml.update({'product_uom_qty': product_uom_qty + item.display_weight})
                            picking_move_line.filtered(lambda a: a.id == ml.id).update({
                                'product_uom_qty': ml.product_uom_qty
                            })
                    stock_quant.sudo().update({
                        'reserved_quantity': item.display_weight
                    })
        else:
            raise models.ValidationError('no se pudo identificar picking')

    @api.multi
    def unreserved_picking(self):
        for item in self:
            stock_move = item.reserved_to_stock_picking_id.move_lines.filtered(
                lambda a: a.product_id == item.stock_production_lot_id.product_id
            )

            move_line = stock_move.move_line_ids.filtered(
                lambda
                    a: a.lot_id.id == item.stock_production_lot_id.id
            )

            if len(move_line) > 1:
                for move in move_line:
                    picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                        lambda a: a.id == move.id
                    )
                    stock_quant = item.stock_production_lot_id.get_stock_quant()

                    stock_quant.sudo().update({
                        'reserved_quantity': stock_quant.total_reserved
                    })

                    item.update({
                        'reserved_to_stock_picking_id': None
                    })

                    for ml in move:
                        if ml.qty_done > 0:
                            raise models.ValidationError('este producto ya ha sido validado')
                        ml.write({'move_id': None, 'product_uom_qty': 0})
                        picking_move_line.filtered(lambda a: a.id == ml.id).write({
                            'move_id': None,
                            'picking_id': None,
                            'product_uom_qty': 0
                        })
            else:
                picking_move_line = item.reserved_to_stock_picking_id.move_line_ids.filtered(
                    lambda a: a.id == move_line.id
                )

                stock_quant = item.stock_production_lot_id.get_stock_quant()
                item.update({
                    'reserved_to_stock_picking_id': None
                })

                for ml in move_line:
                    product_uom_qty = ml.product_uom_qty

                    if ml.qty_done > 0:
                        raise models.ValidationError('este producto ya ha sido validado')

                    ml.update({'product_uom_qty': product_uom_qty - item.display_weight})
                    picking_move_line.filtered(lambda a: a.id == ml.id).update({
                        'product_uom_qty': ml.product_uom_qty
                    })
                item.stock_production_lot_id.update({
                    'available_total_serial': item.stock_production_lot_id.available_total_serial - item.display_weight
                })