from apps.reports.utils import BaseReportsExport, format_data, get_day_header
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from django.conf import settings

class PeopleAttendanceSummaryReport(BaseReportsExport):
    report_title = "People Attendance Summary"
    design_file = "reports/pdf_reports/people_attendance_summary.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'PEOPLEATTENDANCESUMMARY'
    unsupported_formats = ['html', 'json', 'csv']
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
            'data' : format_data(runrawsql(get_query(self.report_name), args=self.args,named_params=True)),
            'report_title': self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
            'report_subtitle_site':f"Site: {sitename}",
            'report_subtitle_date':f"From: {fromdatetime} To {uptodatetime}",
            'header': get_day_header(runrawsql(get_query(self.report_name), args=self.args,named_params=True), fromdatetime, uptodatetime),
        }
        
        return len(self.context['data']) > 0
        
        
    def set_args_required_for_query(self):
        self.args = {
            'timezone':get_timezone(self.formdata['ctzoffset']),
            'siteids':','.join(self.formdata['site']),
            'from':self.formdata['fromdatetime'].strftime('%d/%m/%Y %H:%M:%S'),
            'upto':self.formdata['uptodatetime'].strftime('%d/%m/%Y %H:%M:%S'),
        }  
    
    def execute(self):
        export_format = self.formdata.get('format')
        has_data = self.set_context_data()
        
        if not has_data:
            return None
        
        # preview in pdf
        if self.formdata.get('preview') == 'true':
            export_format = 'pdf'
        
        if export_format == 'pdf':
            return self.get_pdf_output()
        elif export_format == 'xlsx':
            return self.get_xlsx_output()
        