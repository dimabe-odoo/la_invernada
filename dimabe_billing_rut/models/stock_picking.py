from odoo import models, fields, api
import json
import requests
from datetime import date
import re
from pdf417 import encode, render_image, render_svg
import base64
from io import BytesIO 
from math import floor

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    dte_folio = fields.Text(string='Folio DTE')
    dte_type_id =  fields.Many2one(
        'dte.type', string = 'Tipo Documento'
    )
    dte_xml = fields.Text("XML")
    dte_xml_sii = fields.Text("XML SII")
    dte_pdf = fields.Text("PDF")
    ted = fields.Text("TED")
    pdf_url = fields.Text("URL PDF")

    partner_economic_activities = fields.Many2many('custom.economic.activity',related='partner_id.economic_activities')
    company_economic_activities = fields.Many2many('custom.economic.activity', related='company_id.economic_activities')
    partner_activity_id = fields.Many2one('custom.economic.activity', string='Actividad del Proveedor')
    company_activity_id = fields.Many2one('custom.economic.activity', string='Actividad de la Compañía')
    references = fields.One2many(
        'account.invoice.references',
        'invoice_id',
        readonly=False,
        states={'draft': [('readonly', False)]},
    )

    method_of_payment = fields.Selection(
        [
            ('1', 'Contado'),
            ('2', 'Crédito'),
            ('3', 'Gratuito')
        ],
        string="Forma de pago",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='1',
    )

    observations_ids = fields.One2many('custom.invoice.observations','invoice_id',string='Observaciones')

    dispatch_type = fields.Selection([
            ('0', 'Sin Despacho'),
            ('1', 'Despacho por cuenta del receptor del documento'),
            ('2', 'Despacho por cuenta del emisor a instalaciones del cliente'),
            ('3', 'Despacho por cuenta del emisor a otras instalaciones')
            ], 'Tipo de Despacho', default='0')

    transfer_indication  = fields.Selection([
            ('0', 'Sin Translado'),
            ('1', 'Operación constituye venta'),
            ('2', 'Ventas por efectuar'),
            ('3', 'Consignaciones'),
            ('4', 'Entrega gratuita'),
            ('5', 'Traslados internos'),
            ('6', 'Otros traslados no venta'),
            ('7', 'Guía de devolución'),
            ], 'Tipo Translado', default='0')

    date_due = fields.Date(string="Fecha Vencimiento")

    net_amount = fields.Char(string="Neto")

    exempt_amount = fields.Char(string="Exento")

    total = fields.Char(string="Total")



    @api.onchange('partner_id')
    @api.multi
    def _compute_partner_activity(self):
        for item in self:
            activities = []
            for activity in item.partner_id.economic_activities:
                activities.append(activity.id)
            item.partner_activity_id = activities
    

    @api.one
    def send_to_sii(self):
        url = self.env.user.company_id.dte_url
        headers = {
            "apiKey" : self.env.user.company_id.dte_hash,
            "CustomerCode": self.env.user.company_id.dte_customer_code
        }
        invoice = {}
        productLines = []
        lineNumber = 1
        netAmount = 0
        exemtAmount = 0
        countNotExempt = 0
        haveExempt = False

        #Main Validations
        self.validation_fields()

        for item in self.move_ids_without_package:
            if len(self.sale_id.mapped('order_line').filtered(lambda a : a.product_id.id == item.product_id.id).mapped('tax_id')) == 0:
                haveExempt = True
            amount = self.sale_id.order_line.filtered(lambda a : a.product_id.id == item.product_id.id).price_subtotal
            
            quantity = 0
            if item.quantity_done == 0.0:
                quantity = self.sale_id.order_line.filtered(lambda a : a.product_id.id == item.product_id.id).qty_delivered
            else:
                quantity = str(round(item.quantity_done, 6))
            if haveExempt:
                exemtAmount += int(amount)
                productLines.append(
                    {
                        "LineNumber": str(lineNumber),
                        "ProductTypeCode": "EAN",
                        "ProductCode": str(item.product_id.default_code),
                        "ProductName": item.name,
                        "ProductQuantity": str(quantity), # str(round(item.quantity_done, 6)), #segun DTEmite no es requerido int
                        "UnitOfMeasure": str(item.product_id.uom_id.name),
                        "ProductPrice": str(round(item.product_id.lst_price,4)), #segun DTEmite no es requerido int
                        "ProductDiscountPercent": "0",
                        "DiscountAmount": "0",
                        "Amount": str(int(amount)),
                        "HaveExempt": haveExempt,
                        "TypeOfExemptEnum": "1"
                    }
                )
            else:
                netAmount += roundclp(amount)
                productLines.append(
                    {
                        "LineNumber": str(lineNumber),
                        "ProductTypeCode": "EAN",
                        "ProductCode": str(item.product_id.default_code),
                        "ProductName": item.name,
                        "ProductQuantity": str(quantity), # str(round(item.quantity_done, 6)),
                        "UnitOfMeasure": str(item.product_id.uom_id.name),
                        "ProductPrice": str(round(item.product_id.lst_price,4)),
                        "ProductDiscountPercent": "0",
                        "DiscountAmount": "0",
                        "Amount": str(int(amount))
                    }
                )
            lineNumber += 1
        
        if self.partner_id.phone:
            recipientPhone = str(self.partner_id.phone)
        elif self.partner_id.mobile:
            recipientPhone = str(self.partner_id.mobile)
        else:
            recipientPhone = ''

        self.net_amount = str(netAmount)

        self.exempt_amount = str(exemtAmount)

        self.total = str(self.roundclp(netAmount + exemtAmount + self.sale_id.amount_tax))

        invoice= {
            "dteType": self.dte_type_id.code,
            "createdDate": self.scheduled_date.strftime("%Y-%m-%d"),
            "expirationDate": self.date_due.strftime("%Y-%m-%d"), #No hay fecha de vencimiento
            "paymentType": int(self.method_of_payment),
            "dispatchType": str(self.dispatch_type),
            "transferIndication": str(self.transfer_indication),
            "transmitter": {
                "EnterpriseRut": re.sub('[\.]','', "76.991.487-0"), #self.env.user.company_id.invoice_rut,
                "EnterpriseActeco": self.company_activity_id.code,
                "EnterpriseAddressOrigin": self.env.user.company_id.street,
                "EnterpriseCity": self.env.user.company_id.city,
                "EnterpriseCommune": str(self.env.user.company_id.state_id.name),
                "EnterpriseName": self.env.user.company_id.partner_id.name,
                "EnterpriseTurn": self.company_activity_id.name,
                "EnterprisePhone": self.env.user.company_id.phone if self.env.user.company_id.phone else ''
            },
            "recipient": {
                "EnterpriseRut": re.sub('[\.]','', self.partner_id.invoice_rut),
                "EnterpriseAddressOrigin": self.partner_id.street[0:60],
                "EnterpriseCity": self.partner_id.city,
                "EnterpriseCommune": self.partner_id.state_id.name,
                "EnterpriseName": self.partner_id.name,
                "EnterpriseTurn": self.partner_activity_id.name,
                "EnterprisePhone": recipientPhone
            },
            "total": {
                "netAmount": self.net_amount, #str(int(self.sale_id.amount_untaxed)),
                "exemptAmount": self.exempt_amount,
                "taxRate": "19",
                "taxtRateAmount": str(self.roundclp(self.sale_id.amount_tax)),
                "totalAmount":self.total # str(int(self.sale_id.amount_total))
            },
            "lines": productLines,
        }
        
        # Add Refeences
        if self.references and len(self.references) > 0:
            refrenecesList = []
            line_reference_number = 1
            for item in self.references:
                refrenecesList.append(
                    {
                        "LineNumber": str(line_reference_number),
                        "DocumentType": str(item.document_type_reference_id.id),
                        "Folio": str(item.folio_reference),
                        "Date": str(item.document_date),
                        "Code": str(item.code_reference),
                        "Reason": str(item.reason)
                    }
                )
                line_reference_number += 1
            invoice['references'] = refrenecesList
        #Add Additionals
        if len(self.observations_ids) > 0:
            additionals = []
            for item in self.observations_ids:
                additionals.append(item.observations)
            invoice['additional'] =  additionals    


        r = requests.post(url, json=invoice, headers=headers)

        #raise models.ValidationError(json.dumps(invoice))
        jr = json.loads(r.text)

        Jrkeys = jr.keys()
        if 'urlPdf' in Jrkeys and 'filePdf' in Jrkeys and 'folio' in Jrkeys and 'fileXml' in Jrkeys and 'ted' in Jrkeys:
            self.write({'pdf_url':jr['urlPdf']})
            self.write({'dte_pdf':jr['filePdf']})
            self.write({'dte_folio':jr['folio']})
            self.write({'dte_xml':jr['fileXml']})
            self.write({'dte_xml_sii':jr['fileXmlSII']})

            cols = 12
            while True:
                try:
                    if cols == 31:
                        break
                    codes = encode(jr['ted'],cols)
                    image = render_image(codes, scale=5, ratio=2)
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue())
                    self.write({'ted':img_str})
                    break
                except:
                    cols += 1
      
        if 'status' in Jrkeys and 'title' in Jrkeys:
            raise models.ValidationError('Status: {} Title: {} Json: {}'.format(jr['status'],jr['title'],json.dumps(invoice)))
        elif 'message' in Jrkeys:
            raise models.ValidationError('Advertencia: {} Json: {}'.format(jr['message'],json.dumps(invoice)))

    def roundclp(self, value):
        value_str = str(value)
        list_value = value_str.split('.')
        if int(list_value[1]) < 5:
            return floor(value)
        else:
            return round(value)

    def validation_fields(self):
        if not self.partner_id:
            raise models.ValidationError('Por favor selccione el Cliente')
        else:
            if not self.partner_id.invoice_rut:
                raise models.ValidationError('El Cliente {} no tiene Rut de Facturación'.format(self.partner_id.name))

        if not self.dte_type_id.code:
            raise models.ValidationError('Por favor seleccione el Tipo de Documento a emitir')

        if len(self.move_ids_without_package) == 0:
            raise models.ValidationError('Por favor agregar al menos un Producto')

        if not self.company_activity_id or not self.partner_activity_id:
            raise models.ValidationError('Por favor seleccione la Actividad de la Compañía y del Proveedor')

        if len(self.references) > 10:
            raise models.ValidationError('Solo puede generar 20 Referencias')

        if len(self.observations_ids) > 10: 
            raise models.ValidationError('Solo puede generar 10 Observaciones')