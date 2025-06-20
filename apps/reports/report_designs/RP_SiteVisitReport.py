from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from apps.peoples.models import Pgroup
from django.conf import settings
import logging 
logger = logging.getLogger('django')


class RP_SITEVISITREPORT(BaseReportsExport):

    report_title = "RP Site Visit Report"
    design_file = "reports/pdf_reports/rp_sitevisitreport.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'RP_SITEVISITREPORT'
    fields = ['sitegroup*','fromdatetime*', 'uptodatetime*']
    unsupported_formats = ['pdf','html','json','csv']

    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        fromdatetime = self.formdata.get('fromdatetime').strftime('%d/%m/%Y %H:%M:%S')
        uptodatetime = self.formdata.get('uptodatetime').strftime('%d/%m/%Y %H:%M:%S')
        self.set_args_required_for_query()
        self.context = { 
            'base_path':settings.BASE_DIR,
            'data': runrawsql(get_query(self.report_name),args= self.args, named_params=True),
            'report_title':self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
            'report_subtitle':f"From Date:{fromdatetime} To Date:{uptodatetime}"
        }
        return len(self.context['data'])>0
    

    def set_args_required_for_query(self):
        self.args = {
            'timezone':get_timezone(self.formdata['ctzoffset']),
            'sgroupids':','.join(self.formdata['sitegroup']),
            'from':self.formdata['fromdatetime'].strftime('%d/%m/%Y %H:%M:%S'),
            'upto':self.formdata['uptodatetime'].strftime('%d/%m/%Y %H:%M:%S')
        }

    def set_extra_data(self):
        from decimal import Decimal
        from collections import defaultdict
        self.data = runrawsql(get_query(self.report_name),args=self.args,named_params=True)
        site_times = defaultdict(list)

        #Adding Site Name as a key and value as a day and time in list of tuple. 
        for entry in self.data:
            date = entry['endtime_day']
            key = f"{entry['Site Name']}"
            site_times[key].append((entry['endtime_day'], entry['endtime_time']))

        #defaultvalue for any key is dict and default value of any inner key id list 
        formatted_data = defaultdict(lambda: defaultdict(list))

        #key(Site Name) and times(day and time in list of tuple)
        for key, times in site_times.items():
            sorted_times = sorted(times, key=lambda x: (x[0], x[1]))
            for i, (day, time) in enumerate(sorted_times):
                if time == 'Not Performed':
                    time = '--'
                if i % 2 == 0:
                    formatted_data[f"{key}_"][day].append(time)
                else:
                    formatted_data[key][day].append(time)

        Data2 = [{site: [{str(day): time[0]} for day, time in times.items()]} for site, times in formatted_data.items()]
        return Data2

    def create_template(self,route_name, state, solid, site_name, frequency):

        fromdate = int(self.formdata.get('fromdatetime').strftime('%d'))
        uptodate = int(self.formdata.get('uptodatetime').strftime('%d'))

        #created template with out dates
        template = {
            'Route Name/Cluster': route_name, 'State': state, 'Sol Id': solid, 'Site Name': site_name, 'Date': frequency,
        }
        for day in range(fromdate,uptodate+1):  
            template[str(day)] = '--'
        return template

    def merge_data(self,data1, data2):      
        data3 = []
        
        data2_mapping = {}
        for entry in data2:
            #iterating entry for Site Name and times -> [{day,time}]
            for site_name, times in entry.items():
                #iterating times for timeinfo -> day and time  
                for time_info in times:
                    #iterating time_info for day and time 
                    for day, time in time_info.items():
                        if site_name not in data2_mapping:
                            data2_mapping[site_name] = {}
                        data2_mapping[site_name][int(day)] = time

        #iterating on self.data to get entries
        for entry in data1:
            site_name = entry['Site Name']
            site_name_2 = f"{site_name}_" 
            
            if site_name_2 in data2_mapping:
                site_names = [(site_name, '1st'), (site_name_2, '2nd')]
            else:
                site_names = [(site_name, '1st')]
            
            #creating data as in required format for excel
            for name, frequency in site_names:
                template = self.create_template(entry['Route Name/Cluster'], entry['State'], entry['Sol Id'], name, frequency)
                #name in data2_mapping
                if name in data2_mapping:
                    #mapping available dates with their time
                    for day, time in data2_mapping[name].items():
                        template[str(day)] = time
                data3.append(template)

        #Removing all the duplicate datas from data3
        seen = set()
        unique_data = []
        for item in data3:
            frozen_item = frozenset(item.items())
            if frozen_item not in seen:
                seen.add(frozen_item)
                unique_data.append(item.copy())
        return unique_data

    def set_data(self):
        '''
        setting the data which is shown on report
        '''
        self.set_args_required_for_query()
        self.data = runrawsql(get_query(self.report_name),args=self.args,named_params=True)
        Data2 = self.set_extra_data()
        data3 = self.merge_data(self.data,Data2)
        self.data = data3
        return len(self.data)>0 
    
    def set_additional_content(self):
        fromdatetime = self.formdata.get('fromdatetime').strftime('%d/%m/%Y %H:%M:%S')
        uptodatetime = self.formdata.get('uptodatetime').strftime('%d/%m/%Y %H:%M:%S')
        self.additional_content = f"Report: {self.report_title} - From Date: {fromdatetime} To Date: {uptodatetime}"

    def excel_layout(self, worksheet, workbook, df, writer, output):
        super().excel_layout(worksheet, workbook, df, writer, output)

        header_format = workbook.add_format(
            {
                "valign":"middle",
                "fg_color":"#01579b",
                'font_color':'white'
            }
        )
        max_row, max_col = df.shape

        column_setting = [{"header":str(column)} for column in df.columns]

        worksheet.add_table(1,0,max_row,max_col - 1,{"columns":column_setting})

        worksheet.autofit()

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(1,col_num,value,header_format)

        merge_format = workbook.add_format({
            'bg_color':'#E2F4FF',
        }) 
        worksheet.set_column(4, 4, 10)
        worksheet.freeze_panes(0, 5)
        worksheet.merge_range("A1:I1",self.additional_content,merge_format)

        writer.close()

        output.seek(0)
        return output

    def execute(self):
        export_format = self.formdata.get('format')

        if export_format in ['pdf','html']:
            has_data = self.set_context_data()
        else:
            self.set_additional_content()
            has_data = self.set_data()

        if not has_data:
            return None
        
        if self.formdata.get('preview')=='true':
            export_format = 'pdf'

        if export_format == 'pdf':
            return self.get_pdf_output()
        if export_format == 'xls':
            return self.get_xls_output
        if export_format == 'xlsx':
            return self.get_xlsx_output()
        if export_format == 'csv':
            return self.get_csv_output()
        if export_format == 'html':
            return self.get_html_output()
        else: 
            return self.get_json_output()()
