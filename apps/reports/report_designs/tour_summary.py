from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from django.conf import settings


class TourSummaryReport(BaseReportsExport):
    report_title = "Tour Summary"
    design_file = "reports/pdf_reports/tour_summary.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'TOURSUMMARY'
    unsupported_formats = ['None']
    fields = ['site*', 'fromdatetime*', 'uptodatetime*']
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        sitename = Bt.objects.get(id=self.formdata['site']).buname
        self.set_args_required_for_query()
        fromdatetime = self.formdata.get('fromdatetime').strftime('%d/%m/%Y %H:%M:%S')
        uptodatetime = self.formdata.get('uptodatetime').strftime('%d/%m/%Y %H:%M:%S')
        self.context = {
            'base_path': settings.BASE_DIR,
            'data' : runrawsql(get_query(self.report_name), args=self.args,named_params=True),
            'report_title': self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
            'report_subtitle':f"Site: {sitename}, From: {fromdatetime} To {uptodatetime}"
        }
        return len(self.context['data']) > 0
    
    
    def set_args_required_for_query(self):
        self.args = {
            'timezone': get_timezone(self.formdata['ctzoffset']),
            'siteids':self.formdata['site'],
            'from':self.formdata['fromdatetime'].strftime('%d/%m/%Y %H:%M:%S'),
            'upto':self.formdata['uptodatetime'].strftime('%d/%m/%Y %H:%M:%S')
        }
    
    def set_data(self):
        '''
        setting the data which is shown on report
        '''
        self.set_args_required_for_query()
        self.data = runrawsql(get_query(self.report_name), args=self.args, named_params=True)
        return len(self.data) > 0
        
    
    def set_additional_content(self):
        bt = Bt.objects.filter(id=self.client_id).values('id', 'buname').first()
        fromdatetime = self.formdata.get('fromdatetime').strftime('%d/%m/%Y %H:%M:%S')
        uptodatetime = self.formdata.get('uptodatetime').strftime('%d/%m/%Y %H:%M:%S')
        self.additional_content = f"Client: {bt['buname']}; Report: {self.report_title}; From: {fromdatetime} To: {uptodatetime}"

    def excel_columns(self, df):
        df = df[['Date','Total Tours','Total Scheduled','Total Adhoc','Total Completed'
                 ,'Total Pending','Total Closed','Percentage']]
        return df


    def excel_layout(self, worksheet, workbook, df, writer, output):
        super().excel_layout(worksheet, workbook, df, writer, output)
        #overriding to design the excel file
    
        
        # Add a header format.
        header_format = workbook.add_format(
            {
                "valign": "middle",
                "fg_color": "#01579b",
                'font_color':'white'
            }
        )
        max_row, max_col = df.shape
        
        # Create a list of column headers, to use in add_table().
        column_settings = [{"header": column} for column in df.columns]
        
        # Add the Excel table structure. Pandas will add the data.
        worksheet.add_table(1, 0, max_row, max_col - 1, {"columns": column_settings})
        
        # Make the columns wider for clarity.
        #worksheet.set_column(0, max_col - 1, 12)
        worksheet.autofit()
        
        
        # Write the column headers with the defined format.
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(1, col_num, value, header_format)
            
        # Define the format for the merged cell
        merge_format = workbook.add_format({
            'bg_color': '#E2F4FF',
        })
        # Title of xls/xlsx report
        worksheet.merge_range("A1:F1", self.additional_content, merge_format)

        # Close the Pandas Excel writer and output the Excel file
        writer.close()

        # Rewind the buffer
        output.seek(0)
        return output

    def execute(self):
        export_format = self.formdata.get('format')
        # context needed for pdf, html
        if export_format in ['pdf', 'html']:
            has_data = self.set_context_data()
        else:
            self.set_additional_content()
            has_data = self.set_data()
        
        if not has_data:
            return None
        
        # preview in pdf
        if self.formdata.get('preview') == 'true':
            export_format = 'pdf'
        
        if export_format == 'pdf':
            return self.get_pdf_output()
        elif export_format == 'xls':
            return self.get_xls_output()
        elif export_format == 'xlsx':
            return self.get_xlsx_output()
        elif export_format == 'csv':
            return self.get_csv_output()
        elif export_format == 'html':
            return self.get_html_output()
        else:
            return self.get_json_output()
