from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
from django.template.loader import render_to_string
from django_weasyprint.views import WeasyTemplateResponseMixin
import pandas as pd
from django.http import HttpResponse
from apps.activity.models.attachment_model import Attachment
from django.contrib.staticfiles import finders
from django.conf import settings
from django.shortcuts import render
from apps.onboarding.models import Bt
from django.shortcuts import render
from .forms import ReportForm
from .models import ReportHistory
import logging, json
from decimal import Decimal
from datetime import datetime, timedelta
import os
import xlsxwriter

log = logging.getLogger('django')
error_log = logging.getLogger('error_logger')


class BaseReportsExport(WeasyTemplateResponseMixin):
    '''
    A class which contains logic for Report Exports
    irrespective of report design and type. 
    '''
    
    pdf_stylesheets = [
        settings.STATIC_ROOT + 'assets/css/local/reports.css'
    ]
    no_data_error = "No Data"
    report_export_form = ReportForm
    
    def __init__(self, filename, client_id, design_file=None, request=None, context=None,
                 data=None, additional_content=None,
                 returnfile=False,  formdata=None):       
        self.design_file = design_file
        self.request = request
        self.context = context
        self.formdata = formdata
        self.data = data
        self.client_id = client_id
        self.additional_content=additional_content
        self.filename = filename
        self.returnfile = returnfile
    
    
    def get_pdf_output(self):
        try:
            html_string = render_to_string(self.design_file, context=self.context)
            html = HTML(string=html_string, base_url=settings.HOST)
            css_path = finders.find('assets/css/local/reports.css')
            css = CSS(filename=css_path)
            font_config = FontConfiguration()
            pdf_output = html.write_pdf(stylesheets=[css], font_config=font_config, presentational_hints=True)
            if self.returnfile: return pdf_output
            response = HttpResponse(
                pdf_output, content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{self.filename}.pdf"'
            return response
        except Exception as e:
            error_log.error("Error generating PDF", exc_info=True)        

    def write_temporary_pdf(self, pdf_output,workpermit_file_name):

        home_directory = os.path.expanduser("~")
        folder_name    = 'temp_report'
        file_name      = f'{workpermit_file_name}.pdf'
        directory_path = os.path.join(home_directory, folder_name)

        os.makedirs(directory_path, exist_ok=True)

        file_path = os.path.join(directory_path, file_name)
    
        with open(file_path, 'wb') as f:
            f.write(pdf_output)
        
        return file_path
    
    
    def excel_layout(self, worksheet, workbook, df, writer, output):
        '''
        This method is get overriden in inherited/child class
        '''
        log.info("designing the layout...")
        pass
    
    
    def get_excel_output(self, orm):
        worksheet, workbook, df, writer, output = self.set_data_excel(orm=orm)
        output = self.excel_layout(workbook=workbook, worksheet=worksheet,
                          df=df, writer=writer, output=output)
        return output
    
    
    def get_xls_output(self, orm=False):
        log.info("xls is executing")
        output = self.get_excel_output(orm=orm)
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xls"'
        return response
    
    
    def get_xlsx_output(self, orm=False):
        log.info("xlsx is executing")
        if self.formdata['report_name']=='PEOPLEATTENDANCESUMMARY':
            output = self.create_attendance_report()
        else:
            output = self.get_excel_output(orm=orm)
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xlsx"'
        return response
        
    
    def get_csv_output(self):
        log.info("csv is executing")
        df = pd.DataFrame(data=list(self.data))
        df = self.excel_columns(df)
        output = BytesIO()
        df.to_csv(output, index=False, date_format='%Y-%m-%d %H:%M:%S')
        output.seek(0)
        if self.returnfile: return output
        response = HttpResponse(output, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={self.filename}.csv'
        return response
    
    def get_html_output(self):
        log.info("html is executing")
        html_output = render_to_string(self.design_file, context=self.context)
        if self.returnfile: return html_output
        response = render(self.request, self.design_file, self.context)
        return response
    
    def get_json_output(self):
        log.info("json is executing")
        df = pd.DataFrame(list(self.data))
        output = BytesIO()
        df.to_json(output, orient='records', date_format='iso')
        output.seek(0)
        if self.returnfile: return output
        # Create the HttpResponse object with JSON content type and file name
        response = HttpResponse(output, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.json"'
        return response
    
    def get_client_logo(self):
        bt = Bt.objects.get(id=self.client_id)
        uuid, buname = bt.uuid, bt.buname
        log.info("UUID: %s",uuid)
        att = Attachment.objects.get_att_given_owner(uuid)
        log.info("Attachment: %s ", att)
        
        filepath =  att[0]['filepath'][1:]
        if att:
            clientlogo_filepath = settings.MEDIA_URL + filepath + att[0]['filename']
        else:
            clientlogo_filepath = buname
        log.info("Client Logo Path: %s",clientlogo_filepath)
        return clientlogo_filepath
    
    
    def get_col_widths(self, dataframe):
        """
        Get the maximum width of each column in a Pandas DataFrame.
        """
        return [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]

    
    def excel_columns(self, df):
        '''
        Override this method in inherited class
        '''
        return df
 
    
    def set_data_excel(self, orm=False):

        df = pd.DataFrame(list(self.data))
        # Convert the Decimal objects to floats using the float() function
        df = df.applymap(lambda x: float(x) if isinstance(x, Decimal) else x)
        df = self.excel_columns(df)
        # Create a Pandas Excel writer using XlsxWriter as the engine and BytesIO as file-like object
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter',  datetime_format='yyyy-mm-dd hh:mm:ss', date_format="mm dd yyyy",)
        workbook = writer.book
        if orm:
            worksheet = workbook.add_worksheet('Sheet1')
        else:
            df.to_excel(writer, index=False, sheet_name='Sheet1', startrow=2, header=False)
            worksheet = writer.sheets['Sheet1']

        return worksheet, workbook, df, writer, output
    
    def write_custom_mergerange(self, worksheet, workbook, custom_merge_ranges):
        for merge_item in custom_merge_ranges:
            format = workbook.add_format = merge_item['format']
            range = merge_item['range']
            content = merge_item.get('content')
            worksheet.merge_range(range, content, format)
        return worksheet, workbook
    
    def create_attendance_report(self):
        data = self.context['data']
        header = self.context['header']
        report_title = self.context['report_title']
        report_subtitle_site = self.context['report_subtitle_site']
        report_subtitle_date = self.context['report_subtitle_date']

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('People Attendance Summary')

        # Define styles
        title_style = workbook.add_format({'font_size': 12, 'bold': True, 'align': 'center', 'border': 1})
        subtitle_style = workbook.add_format({'font_size': 10, 'align': 'center', 'border': 1})
        header_style = workbook.add_format({'font_size': 10, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E0E8F1', 'border': 1})
        cell_style = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
        total_style = workbook.add_format({'font_size': 10, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E0E8F1', 'border': 1})
        sunday_style = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'bg_color': '#FF6F6F'})
        less_than_8_style = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'bg_color': 'yellow'})
        less_than_4_style = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'bg_color': '#FFA500'})

        num_columns = len(header[0]) + 6
        # Add title and subtitle
        worksheet.merge_range(0, 0, 0, num_columns - 1, report_title, title_style)
        worksheet.merge_range(1, 0, 1, num_columns - 1, report_subtitle_site, subtitle_style)
        worksheet.merge_range(2, 0, 2, num_columns - 1, report_subtitle_date, subtitle_style)

        # Set row height for rows 0 through 5
        for row in range(6):
            worksheet.set_row(row, 20)

        # Start the table from row 4
        current_row = 4

        # Add headers
        headers = ['Department', 'Designation', 'People Code', 'People Name', 'Values'] + header[0] + ['Total Hr\'s']
        for col, header_text in enumerate(headers):
            worksheet.write(current_row, col, header_text, header_style)

        current_row += 1

        # Add day names and apply Sunday style to entire column
        for col, day_name in enumerate(header[1], start=5):
            worksheet.write(current_row, col, day_name, header_style)
            if day_name == 'Sun':
                for row in range(current_row + 1, 180):  # Apply to all rows
                    worksheet.write(row, col, None, sunday_style)

        current_row += 1

        # Add data
        for department, designations in data[0].items():
            dept_start_row = current_row
            for designation, people in designations.items():
                design_start_row = current_row
                for person_code, records in people.items():
                    person_start_row = current_row
                    worksheet.write(current_row, 0, department, cell_style)
                    worksheet.write(current_row, 1, designation, cell_style)
                    worksheet.write(current_row, 2, person_code, cell_style)
                    worksheet.write(current_row, 3, records[0]['peoplename'], cell_style)

                    total_minutes = 0

                    for i, value_type in enumerate(['IN', 'OUT', 'Total Hr\'s']):
                        worksheet.write(current_row + i, 4, value_type, cell_style)

                        for day_number in header[0]:
                            col = header[0].index(day_number) + 5
                            day_records = [r for r in records if r['day'] == day_number]
                            style = cell_style
                            
                            if day_records:
                                record = day_records[0]
                                if value_type == 'IN':
                                    cell_value = record['punch_intime']
                                elif value_type == 'OUT':
                                    cell_value = record['punch_outtime']
                                else:  # Total hr's
                                    cell_value = record['totaltime']
                                    # Calculate total time
                                    hours, minutes = map(int, record['totaltime'].split(':'))
                                    total_minutes += hours * 60 + minutes
                                    
                                    # Apply conditional formatting based on total time
                                    if hours < 4:
                                        style = less_than_4_style
                                    elif hours < 8:
                                        style = less_than_8_style
                                
                                worksheet.write(current_row + i, col, cell_value, style)

                    # Calculate and add total hours
                    total_hours, total_minutes = divmod(total_minutes, 60)
                    total_time = f"{total_hours:02d}:{total_minutes:02d}"
                    worksheet.merge_range(person_start_row, len(headers) - 1, person_start_row + 2, len(headers) - 1, total_time, total_style)

                    current_row += 3

                # Merge designation cells
                if design_start_row < current_row - 1:
                    worksheet.merge_range(design_start_row, 1, current_row - 1, 1, designation, cell_style)

            # Merge department cells
            if dept_start_row < current_row - 1:
                worksheet.merge_range(dept_start_row, 0, current_row - 1, 0, department, cell_style)

        # Adjust column widths
        worksheet.set_column(0, 1, 12)  # Columns A-B (Department, Designation)
        worksheet.set_column(2, 2, 10)  # Columns C (People Code)
        worksheet.set_column(3, 3, 26)  # Columns D (People Name)
        worksheet.set_column(4, 4, 8)   # Column E (Values)
        worksheet.set_column(5, len(headers) - 2, 6)  # Date columns
        worksheet.set_column(len(headers) - 1, len(headers) - 1, 10)  # Total column
        worksheet.set_default_row(15)  # Set default row height
        worksheet.freeze_panes(6, 5)
        workbook.close()

        # Seek to the beginning of the BytesIO object
        output.seek(0)

        return output  
            

class ReportEssentials(object):
    '''
    Report Essentials are the details
    requred by ReportExport functioning.
    '''
    # report_names
    TaskSummary                = 'TASKSUMMARY'
    TourSummary                = 'TOURSUMMARY'
    ListOfTasks                = 'LISTOFTASKS'
    ListOfTickets              = 'LISTOFTICKETS'
    PPMSummary                 = 'PPMSUMMARY'
    SiteReport                 = 'SITEREPORT'
    ListOfTours                = 'LISTOFTOURS'
    DynamicTourList            = 'DYNAMICTOURLIST'
    StaticTourList            = 'STATICTOURLIST'
    WorkOrderList              = 'WORKORDERLIST'
    SiteVisitReport            = 'SITEVISITREPORT'
    PeopleQR                   = 'PEOPLEQR'
    AssetQR                    = 'ASSETQR'
    CheckpointQR               = 'CHECKPOINTQR'
    LocationQR                 = 'LOCATIONQR'
    AssetwiseTaskStatus        = 'ASSETWISETASKSTATUS'
    StaticDetailedTourSummary  = 'STATICDETAILEDTOURSUMMARY'
    TourDetails                = 'TourDetails'
    StaticTourDetails          = 'STATICTOURDETAILS'
    DynamicTourDetails         = 'DYNAMICTOURDETAILS'
    DynamicDetailedTourSummary = 'DYNAMICDETAILEDTOURSUMMARY'
    LogSheet                   = 'LOGSHEET'
    RP_SiteVisitReport         = 'RP_SITEVISITREPORT'
    PeopleAttendanceSummary    = 'PEOPLEATTENDANCESUMMARY'
    
    def __init__(self, report_name):
        self.report_name = report_name

    def get_report_export_object(self):
        # Report Design Files
        from apps.reports.report_designs.task_summary import TaskSummaryReport
        from apps.reports.report_designs.tour_summary import TourSummaryReport
        from apps.reports.report_designs.ppm_summary import PPMSummaryReport
        from apps.reports.report_designs.sitereport import SiteReportFormat
        from apps.reports.report_designs.list_of_task import ListofTaskReport
        from apps.reports.report_designs.list_of_tickets import ListofTicketReport
        from apps.reports.report_designs.list_of_tours import ListofTourReport
        from apps.reports.report_designs.work_order_list import WorkOrderList
        from apps.reports.report_designs.site_visit_report import SiteVisitReport
        from apps.reports.report_designs.qrcode_report import PeopleQR
        from apps.reports.report_designs.qrcode_report import AssetQR
        from apps.reports.report_designs.qrcode_report import CheckpointQR
        from apps.reports.report_designs.assetwise_task_status import AssetwiseTaskStatus
        from apps.reports.report_designs.static_detailed_tour_summary import StaticDetailedTourSummaryReport
        from apps.reports.report_designs.dynamic_tour_details import DynamicTourDetailReport
        from apps.reports.report_designs.static_tour_details import StaticTourDetailReport
        from apps.reports.report_designs.dynamic_detailed_tour_summary import DynamicDetailedTourSummaryReport
        from apps.reports.report_designs.log_sheet import LogSheet
        from apps.reports.report_designs.RP_SiteVisitReport import RP_SITEVISITREPORT
        from apps.reports.report_designs.dynamic_tour_list import DynamicTourList
        from apps.reports.report_designs.static_tour_list import StaticTourList
        from apps.reports.report_designs.qrcode_report import LocationQR
        from apps.reports.report_designs.people_attendance_summary import PeopleAttendanceSummaryReport

        return {
            self.TaskSummary: TaskSummaryReport,
            self.TourSummary:TourSummaryReport,
            self.PPMSummary:PPMSummaryReport,
            self.SiteReport:SiteReportFormat,
            self.ListOfTasks:ListofTaskReport,
            self.ListOfTickets:ListofTicketReport,
            self.ListOfTours:ListofTourReport,
            self.WorkOrderList:WorkOrderList,
            self.SiteVisitReport:SiteVisitReport,
            self.PeopleQR:PeopleQR,
            self.AssetQR:AssetQR,
            self.CheckpointQR:CheckpointQR,
            self.LocationQR:LocationQR,
            self.AssetwiseTaskStatus:AssetwiseTaskStatus,
            self.StaticDetailedTourSummary:StaticDetailedTourSummaryReport,
            self.DynamicDetailedTourSummary:DynamicDetailedTourSummaryReport,
            self.StaticTourDetails:StaticTourDetailReport,
            self.DynamicTourDetails:DynamicTourDetailReport,
            self.LogSheet:LogSheet,
            self.RP_SiteVisitReport:RP_SITEVISITREPORT,
            self.DynamicTourList:DynamicTourList,
            self.StaticTourList:StaticTourList,
            self.PeopleAttendanceSummary:PeopleAttendanceSummaryReport
        }.get(self.report_name)
    
    @property
    def behaviour_json(self):
        report = self.get_report_export_object()
        return {
            'unsupported_formats': report.unsupported_formats,
            'fields':report.fields
        }
    
        
def create_report_history(
    has_data, params, report_name, export_type, 
    user_id, ctzoffset, bu_id, client_id, traceback=None, cc=None,
    to=None, email_body=None, 
):
    return ReportHistory.objects.create(
        has_data=has_data,
        params=json.dump(params),
        bu_id=bu_id,
        client_id=client_id,
        report_name=report_name,
        user_id=user_id,
        ctzoffset=ctzoffset,
        cc_mails=cc,
        to_mails=to,
        email_body=email_body,
        traceback=traceback,
        export_type=export_type
    )
    
def process_sendingreport_on_email(fileresponse, formdata, email):
    try:
        from background_tasks.report_tasks import save_report_to_tmp_folder
        from background_tasks.tasks import send_generated_report_onfly_email
        filepath = save_report_to_tmp_folder(filename=formdata['report_name'], ext=formdata['format'], report_output=fileresponse)
        send_generated_report_onfly_email.delay(filepath, email, formdata['to_addr'], formdata['cc'], formdata['ctzoffset'])
    except Exception as e:
        log.critical("something went wrong while sending report on email", exc_info=True)

def find_file(file_name, search_path='/'):
    for root, dirs, files in os.walk(search_path):
        if file_name in files:
            # Construct the full path to the file
            file_path = os.path.join(root, file_name)
            return file_path
    # If file is not found
    return None

def trim_filename_from_path(file_path):
    filename = os.path.basename(file_path)  # Get the filename from the path
    trimmed_path = file_path[:-len(filename)]  # Remove the filename from the path
    return trimmed_path

def format_data(data):
    output = {}
    # Process each entry in the data
    for entry in data:
        department = entry['department'] if entry['department'] != "NONE" else "--"
        designation = entry['designation'] if entry['designation'] != "NONE" else "--"
        peoplecode = entry['peoplecode']
        
        # Create nested dictionaries if they don't exist
        if department not in output:
            output[department] = {}
        
        if designation not in output[department]:
            output[department][designation] = {}
        
        if peoplecode not in output[department][designation]:
            output[department][designation][peoplecode] = []
        
        # Convert Decimal('day') to integer and prepare the entry
        formatted_entry = {
            'peoplename' : entry['peoplename'],
            'day': int(entry['day']),  # Convert Decimal to int
            'day_of_week': entry['day_of_week'].strip(),  # Optionally strip whitespace
            'punch_intime': entry['punch_intime'],
            'punch_outtime': entry['punch_outtime'],
            'totaltime': entry['totaltime'],
        }
        
        # Append the entry to the corresponding department and designation
        output[department][designation][peoplecode].append(formatted_entry)
    
    output_list = [output]
    return output_list

def generate_days_in_range(start_datetime, end_datetime):
    """Generate a list of tuples with day of the month, day names, and month names for a given datetime range."""
    days = []
    current_datetime = start_datetime
    while current_datetime <= end_datetime:
        day_of_month = current_datetime.day
        day_name = current_datetime.strftime('%a')  # Day of the week abbreviation
        month_name = current_datetime.strftime('%b')  # Month abbreviation
        days.append((day_of_month, day_name, month_name))
        current_datetime += timedelta(days=1)
    return days

def get_day_header(data, start_date_str, end_date_str):
    # Parse the input datetime range
    start_datetime = datetime.strptime(start_date_str, '%d/%m/%Y %H:%M:%S')
    end_datetime = datetime.strptime(end_date_str, '%d/%m/%Y %H:%M:%S')
    
    # Generate the complete list of days for the given range
    all_days = generate_days_in_range(start_datetime, end_datetime)
    
    # Prepare lists for all days in the range
    all_day_numbers = [day for day, _, _ in all_days]
    all_day_names = [day_name for _, day_name, _ in all_days]
    
    # Create a mapping for days with data (for debugging purposes)
    day_mapping = {}
    for entry in data:
        day_str = entry['day']
        month_str = entry.get('month', start_datetime.strftime('%m'))
        year_str = entry.get('year', start_datetime.strftime('%Y'))
        date_key = f"{year_str}-{month_str}-{day_str}"
        day_mapping[date_key] = entry['day_of_week'].strip()[:3]
    
    # Print debug information
    for i, (day, day_name, _) in enumerate(all_days):
        current_date = start_datetime + timedelta(days=i)
        date_key = current_date.strftime("%Y-%m-%d")
    
    final_list = [all_day_numbers, all_day_names]
    return final_list
