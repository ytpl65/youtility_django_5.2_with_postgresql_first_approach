from apps.reports.utils import BaseReportsExport
from apps.work_order_management.models import Wom
from apps.work_order_management.utils import get_last_12_months_sla_reports,get_sla_report_approvers,get_month_number
from django.conf import settings
from datetime import datetime



class ServiceLevelAgreement(BaseReportsExport):
    report_title = 'Service Level Agreement'
    design_file = "reports/pdf_reports/service_level_agreement.html"
    report_name = "ServiceLevelAgreement"

    def __init__(self, filename, client_id=None, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id=client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        from apps.work_order_management.views import SLA_View
        from apps.work_order_management.models import WomDetails
        monthly_choices = SLA_View.MONTH_CHOICES
        wom = Wom.objects.get(id=self.formdata.get('id'))
        is_month_present = wom.other_data.get('month',None)
        if not is_month_present:
            month_no = wom.cdtz.month -1
            if month_no == 0:
                month_no = 12
                year = wom.cdtz.year -1
            else:
                year = wom.cdtz.year
            month_name = monthly_choices.get(f'{month_no}')
        else:
            month_name = is_month_present
            year = wom.cdtz.year
            if month_name == 'December' and datetime.now().month>=1:
                year = wom.cdtz.year - 1
            else:
                pass
        sla_answers_data,overall_score,question_ans,all_average_score,remarks = Wom.objects.sla_data_for_report(self.formdata.get('id'))
        wom_details = Wom.objects.filter(id=self.formdata.get('id')).values_list('vendor_id','bu_id','bu_id__buname','other_data','vendor_id__name','vendor_id__description','workpermit')
        vendor_id = wom_details[0][0]
        site_id = wom_details[0][1]
        sitename = wom_details[0][2]
        sla_report_approvers = get_sla_report_approvers(wom_details[0][3]['wp_approvers'])
        vendor_name = wom_details[0][4]
        vendor_description = wom_details[0][5]
        workpermit_status = wom_details[0][6]
        month_number = get_month_number(monthly_choices,month_name)
        sla_last_three_month_report = get_last_12_months_sla_reports(vendor_id=vendor_id,bu_id=site_id,month_number=month_number)
        month_year = f"{month_name} {year}"
        wom = Wom.objects.filter(parent_id=self.formdata.get('id')).order_by('-id')[1]
        wom_details = WomDetails.objects.filter(wom_id=wom.id)
        if wom_details[0].qset.qsetname=='KPI As Per Agreement':
            response_time = wom_details[0].answer
            resolution_time = wom_details[1].answer
            uptime_score = wom_details[2].answer
        else:
            response_time = '-'
            resolution_time = '-'
            uptime_score = '-'
        self.context = {
                'question_answer': question_ans,
                'sla_answer_data': sla_answers_data,
                'overall_score':overall_score,
                'average_score':all_average_score,
                'remarks':remarks,
                'vendor_name':vendor_name,
                'vendor_description':vendor_description,
                'sitename':sitename,
                'sla_last_three_month_report':sla_last_three_month_report,
                'sla_report_approvers':sla_report_approvers,
                'month_year':month_year,
                'workpermit_status':workpermit_status,
                "uptime_score":uptime_score,
                "response_time":response_time,
                "resolution_time":resolution_time

        }
    
    def execute(self):
        self.set_context_data()
        return self.get_pdf_output()
    


    