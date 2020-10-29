import xlsxwriter
from odoo import models


class HrPaySlipXlsx(models.AbstractModel):
    _name = 'report.dimabe_billing_rut.remunerations_book'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        payslip = self.env['hr.payslip'].search([])
        report_name = "Libro de Remuneraciones"
        # One sheet by partner
        indicadores_id = payslip.mapped('indicadores_id').mapped('name')
        sheet = workbook.add_worksheet('Libro de Remuneraciones')
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        merge_format_data = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        sheet.merge_range(
            "B2:E2", "Informe: Libro de Remuneraciones", merge_format)
        sheet.merge_range("B3:E3", "Mes a procesar : {}".format(
            indicadores_id[-1]), merge_format)
        employees = self.env['hr.employee'].search([('address_id', '=', 423)])
        headers = ['Nombre', 'Rut', 'Dias Trabajados', 'Sueldo Base', 'Grat. Legal', 'Horas Extras', 'Bonos Imponibles', 'Aguinaldo Fiestas Patrias', 'Aguinaldo Navidad', 'Horas de Descuento', 'Total Imponible', 'Colacion', 'Movilizacion', 'Asig. Familiar', 'Asig. Varias', 'Total No Imponible',
                  'Total Haberes', 'AFP', 'Salud', 'Seg. Cesantia', 'Impto. Unico', 'Otros AFP', 'Anticipos', 'Anticipo Aguinaldo', 'Credito Social', 'Ahorro AFP', 'Ahorro APV', 'Ahorro CCAF', 'Seg. de Vida CCAF', 'Ptmo. Empresa', 'Retencion Judicial', 'Total Descuentos', 'Liquido A Pagar']
        
        
        column_head = 1
        row = 8
        column = 8
        letter_a = "A" 
        letter_b = "E"
        
        
        for head in headers :
            sheet.write(6,column_head,head)
            column_head += 1
        for employee in employees:
            x = chr(ord(letter_a) + 3)
            y = chr(ord(letter_a) + 3)
            if employee.id == employees[0].id:
                sheet.merge_range(x+str(row - 1)+":"+y+str(row - 1),'Nombre:',merge_format)
                sheet.merge_range("E"+str(row - 1)+":"+"D"+str(row - 1),'RUT:',merge_format)
            to_merge = "A"+str(row)+":"+"D"+str(row)
            sheet.merge_range(to_merge,employee.name,merge_format_data)
            row += 1

        bold = workbook.add_format({'bold': True})
