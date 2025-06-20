from apps.reports.utils import BaseReportsExport
from apps.core.utils import get_timezone
from apps.work_order_management.models import Wom
from django.conf import settings
import pytz



class WorkPermit(BaseReportsExport):
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        id = self.formdata.get('id')
        wp_info, wp_sections, rwp_section, sitename = Wom.objects.wp_data_for_report(id)
        approvers = WorkPermit.__get_approvers_name(id)
        verifiers = WorkPermit.__get_verifiers_name(id)
        verifiers_status = Wom.objects.get(id=id).verifiers_status
        approver_status  = Wom.objects.get(id=id).workpermit
        workpermit_no = Wom.objects.get(id=id).other_data['wp_seqno']
        vendor_name = Wom.objects.get(id=id).vendor.name
        wp_sections_without_email_sections = [section for section in wp_sections if section.get('section')!='EMAIL']
        utc_now = Wom.objects.get(id=id).mdtz
        ist_timezone = pytz.timezone('Asia/Kolkata')
        current_time_ist = utc_now.astimezone(ist_timezone)
        formatted_time = current_time_ist.strftime("%d-%b-%Y %H:%M:%S")
        self.context = {
            'base_path': settings.BASE_DIR,
            'main_title':sitename,
            'report_subtitle':self.report_title,
            'wp_info' : wp_info,
            'wp_sections': wp_sections_without_email_sections,
            'rwp_info':[rwp_section],
            'report_title': self.report_title,
            'app_logo':self.ytpl_applogo,
            'approvers':approvers,
            'verifiers':verifiers,
            'verifiers_status':verifiers_status,
            'approvers_status':approver_status,
            'current_time': formatted_time,
            'vendor_name':vendor_name,
            'workpermit_no':workpermit_no
        }


    def set_args_required_for_query(self):
        self.args = [
            get_timezone(self.formdata['ctzoffset']),
            self.formdata['site'],
            self.formdata['fromdate'].strftime('%d/%m/%Y'),
            self.formdata['uptodate'].strftime('%d/%m/%Y'),
            ]

    def execute(self):
        self.set_context_data()
        return self.get_pdf_output()
    
    def __get_approvers_name(id):
        obj = Wom.objects.filter(id=id).values('other_data').first()
        approver = []
        for record in obj['other_data']['wp_approvers']:
            if record['status'] == 'APPROVED':
                approver.append(record['name']) 
        return approver

    def __get_verifiers_name(id):
        obj = Wom.objects.filter(id=id).values('other_data').first()
        verifier = []
        for record in obj['other_data']['wp_verifiers']:
            if record['status'] == 'APPROVED':
                verifier.append(record['name'])
        return verifier


class ColdWorkPermit(WorkPermit):
    report_title = 'COLD WORK PERMIT'
    design_file = "reports/pdf_reports/cold_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ColdWorkPermit'
    
class HotWorkPermit(WorkPermit):
    report_title = 'HOT WORK PERMIT'
    design_file = "reports/pdf_reports/hot_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'HotWorkPermit'

class HeightWorkPermit(WorkPermit):
    report_title = 'HEIGHT WORK PERMIT'
    design_file = "reports/pdf_reports/height_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'HeightWorkPermit'

class ConfinedSpaceWorkPermit(WorkPermit):
    report_title = 'CONFINED SPACE WORK PERMIT'
    design_file = "reports/pdf_reports/confined_space_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ConfinedSpaceWorkPermit'

class ElectricalWorkPermit(WorkPermit):
    report_title = 'ELECTRICAL WORK PERMIT'
    design_file = "reports/pdf_reports/electrical_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ElectricalWorkPermit'

class EntryRequest(WorkPermit):
    report_title = 'Entry Request'
    design_file = "reports/pdf_reports/entry_request.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'EntryRequest'
