from django import forms
from apps.activity import models as am
from apps.onboarding import models as om
from apps.peoples import models as pm
from apps.core import utils
from django_select2 import forms as s2forms
from django.db.models import Q
from datetime import datetime, timedelta
from django.conf import settings
from apps.activity.models.location_model import Location
from apps.activity.models.question_model import QuestionSet
from apps.activity.models.asset_model import Asset
from apps.reports.models import ScheduleReport, GeneratePDF
from enum import Enum

class MasterReportTemplate(forms.ModelForm):
    required_css_class = "required"
    showto_allsites    = forms.BooleanField(initial = False, required = False, label='Show to all sites')
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), label="Site Types", required=False)
    buincludes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), label='Site Includes', required=False)
    site_grp_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), label='Site groups', required=False)


    class Meta:
        model = QuestionSet
        fields = [
            'type',  'qsetname', 'buincludes', 'site_grp_includes', 
            'site_type_includes', 'enable', 'ctzoffset']
        labels = {
            'qsetname':'Template Name',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tatype__tacode = "SITETYPE") | Q(tacode='NONE')).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_sites_of_client(self.request.session['client_id']).values_list('id', flat=True)
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist)).values_list('id', 'groupname')
        


class SiteReportTemplate(MasterReportTemplate):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['type'].initial = QuestionSet.Type.SITEREPORTTEMPLATE
        self.fields['type'].widget.attrs = {'style': 'display:none'}
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1

class IncidentReportTemplate(MasterReportTemplate):
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].initial = QuestionSet.Type.INCIDENTREPORTTEMPLATE
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1



class TestForm(forms.Form):
    firstname  = forms.CharField(max_length=10, required=False)
    lastname   = forms.CharField(max_length=10, required=True)
    middlename = forms.CharField(max_length=10, required=True)




class ReportBuilderForm(forms.Form):
    model = forms.ChoiceField(label="Model", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), help_text="Select a model where you want data from")
    columns = forms.MultipleChoiceField(label="Coumns", widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), help_text="Select columns required in the report")
    

def get_report_templates():
    return  

class ReportForm(forms.Form):
    required_css_class = "required"
    report_templates = [
        ('', 'Select Report'),
        ('TASKSUMMARY', 'Task Summary'),
        ('TOURSUMMARY', 'Tour Summary'),
        ('LISTOFTASKS', 'List of Tasks'),
        ('LISTOFTOURS', 'List of Internal Tours'),
        ('DYNAMICTOURLIST','Dynamic Tour List'),
        ('STATICTOURLIST','Static Tour List'),
        ('PPMSUMMARY', 'PPM Summary'),
        ('LISTOFTICKETS', 'List of Tickets'),
        ('WORKORDERLIST', 'Work Order List'),
        ('SITEREPORT', 'Site Report'),
        ('PEOPLEQR', 'People-QR'),
        ('ASSETQR', 'Asset-QR'),
        ('CHECKPOINTQR', 'Checkpoint-QR'),
        ('LOCATIONQR','Location-QR'),
        ('ASSETWISETASKSTATUS','Assetwise Task Status'),
        ('STATICDETAILEDTOURSUMMARY','Static Detailed Tour Summary'),
        ('DYNAMICDETAILEDTOURSUMMARY','Dynamic Detailed Tour Summary'),
        ('DYNAMICTOURDETAILS','Dynamic Tour Details'),
        ('STATICTOURDETAILS','Static Tour Details'),
        ('SITEVISITREPORT','SiteVisitReport'),
        ('LOGSHEET','Log Sheet'),
        ('RP_SITEVISITREPORT','Route Plan Site Visit Report'),
        ('PEOPLEATTENDANCESUMMARY','People Attendance Summary')
    ]
    download_or_send_options = [
        ('DOWNLOAD', 'Download'),
        ('SEND', 'Email'),
    ]
    format_types = [
        ('', 'Select Format'),
        ('pdf', 'PDF'),
        ('xlsx', 'XLSX'),
        ('html', 'HTML'),
        ('json', 'JSON'),
        ('csv', 'CSV'),
    ]
    SIZES = [
        (120, 'Small'),
        (200, 'Medium'),
        (300, 'Large'), 
    ]
    
    People_or_Site_CHOICES = [('PEOPLE', 'People'), ('SITE', 'Site')]
    Asset_or_Site_CHOICES = [('ASSET','Asset'),('SITE','Site')]
    Checkpoint_or_Site_CHOICES = [('CHECKPOINT','Checkpoint'),('SITE','Site')]
    Location_or_Site_CHOICES = [('LOCATION','Location'),('SITE','Site')]
    
    # data fields
    report_name     = forms.ChoiceField(label='Report Name', required=True, choices=report_templates, initial='TASK_SUMMARY')
    site            = forms.ChoiceField(label='Site', required = False, widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    sitegroup       = forms.MultipleChoiceField(label="Site Group", required=False, widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }))
    fromdate        = forms.DateField(label='From Date', required=False,input_formats=['%d-%b-%Y', '%Y-%m-%d'])
    fromdatetime    = forms.DateTimeField(label='From Date Time', required=False,input_formats=['%d-%b-%Y %H:%M', '%Y-%m-%d %H:%M:%S'])
    uptodate        = forms.DateField(label='To Date', required=False,input_formats=['%d-%b-%Y', '%Y-%m-%d'])
    uptodatetime    = forms.DateTimeField(label='To Date Time', required=False,input_formats=['%d-%b-%Y %H:%M', '%Y-%m-%d %H:%M:%S'])
    asset           = forms.ChoiceField(label="Asset", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    qset            = forms.ChoiceField(label="Question Set", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    assettype       = forms.ChoiceField(label="Asset Type", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    checkpoint      = forms.CharField(label='Checkpoint', widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    location        = forms.CharField(label='Location', widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    checkpoint_type = forms.CharField(label='Checkpoint Type', widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    location_type   = forms.CharField(label='Location Type', widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    ticketcategory  = forms.CharField(label='Ticket Category', widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=False)
    peoplegroup     = forms.ChoiceField(label="People Group", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False, choices=[])
    people          = forms.ChoiceField(label="People", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False, choices=[])
    mult_people     = forms.MultipleChoiceField(label="People", widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=False, choices=[])
    mult_asset      = forms.MultipleChoiceField(label="Asset",widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=False, choices=[])
    mult_checkpoint = forms.MultipleChoiceField(label="Checkpoint",widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=False, choices=[])
    mult_location   = forms.MultipleChoiceField(label="Location",widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=False, choices=[])
    qrsize          = forms.ChoiceField(label="QR Size", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), choices=SIZES, initial=120, required=False)
    assetcategory   = forms.ChoiceField(label="Asset Category", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), required=False)
    site_or_people  = forms.ChoiceField(label="Site/People", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),choices=People_or_Site_CHOICES, required=False)
    site_or_asset  = forms.ChoiceField(label="Site/Asset", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),choices=Asset_or_Site_CHOICES, required=False)
    site_or_checkpoint  = forms.ChoiceField(label="Site/Checkpoint", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),choices=Checkpoint_or_Site_CHOICES, required=False)
    site_or_location  = forms.ChoiceField(label="Site/Location", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),choices=Location_or_Site_CHOICES, required=False)
    
    #other form fields
    format      = forms.ChoiceField(widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), label="Format", required=True, choices=format_types)
    export_type = forms.ChoiceField(widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), label='Get File with', required=True, choices=download_or_send_options, initial='DOWNLOAD')
    cc          = forms.MultipleChoiceField(label='CC', required=False, widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }))
    to_addr     = forms.MultipleChoiceField(label="To", required=False, widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }))
    preview     = forms.CharField(widget=forms.HiddenInput,required=False, initial="false")
    email_body  = forms.CharField(label='Email Body', max_length=500, required=False, widget=forms.Textarea(attrs={'rows':2}))
    ctzoffset   = forms.IntegerField(required=False)

    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['site'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(S.get('_auth_user_id'), True)
        self.fields['sitegroup'].choices = [("", "")] + list(pm.Pgroup.objects.filter(
            identifier__tacode="SITEGROUP",
            bu_id__in = S['assignedsites'],
            enable=True).values_list('id', 'groupname'))
        self.fields['peoplegroup'].choices = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True, choices=True)
        self.fields['people'].choices = self.fields['mult_people'].choices = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True, choices=True)
        self.fields['asset'].choices = self.fields['mult_asset'].choices = Asset.objects.asset_choices_for_report(self.request,sitewise=True,choices=True,identifier = 'ASSET')
        self.fields['location'].choices = self.fields['mult_location'].choices = Location.objects.location_choices_for_report(self.request,sitewise=True,choices=True)
        self.fields['checkpoint'].choices = self.fields['mult_checkpoint'].choices = Asset.objects.asset_choices_for_report(self.request,sitewise=True,choices=True,identifier = 'CHECKPOINT')
        self.fields['assettype'].choices  = Asset.objects.asset_type_choices_for_report(self.request)
        self.fields['location_type'].choices  = Location.objects.location_type_choices_for_report(self.request)
        self.fields['assetcategory'].choices = Asset.objects.asset_category_choices_for_report(self.request)
        self.fields['qset'].choices = QuestionSet.objects.qset_choices_for_report(self.request)
        self.fields['fromdate'].initial = self.get_default_range_of_dates()[0]
        self.fields['uptodate'].initial = self.get_default_range_of_dates()[1]
        self.fields['cc'].choices = pm.People.objects.filter(isverified=True, client_id = S['client_id']).values_list('email', 'peoplename')
        self.fields['to_addr'].choices = pm.People.objects.filter(isverified=True, client_id = S['client_id']).values_list('email', 'peoplename')
        utils.initailize_form_fields(self)
        
        
    def get_default_range_of_dates(self):
        today = datetime.now().date()
        first_day_of_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        return first_day_of_last_month, last_day_of_last_month

    def clean(self):
        cd = super().clean()
        if cd['report_name'] == 'SITEREPORT' and cd.get('people') in ["", None] and cd.get('sitegroup') in ["", None]:
            raise forms.ValidationError(
                f"Both Site Group and People cannot be empty, when the report is {cd.get('report_name')}")
        
        self.validate_date_range(cd, 'fromdate', 'uptodate', 'From date cannot be greater than To date')
        self.validate_date_range(cd, 'fromdatetime', 'uptodatetime', 'From datetime cannot be greater than To datetime')

        if cd.get('format') != 'pdf': self.cleaned_data['preview'] = "false"
        return cd

    def validate_date_range(self, cd, field1, field2, error_msg):
        date1 = cd.get(field1)
        date2 = cd.get(field2)
        
        if date1 and date2 and date1 > date2:
            raise forms.ValidationError(error_msg)

        if date1 and date2 and (date2 - date1).days > 31:
            raise forms.ValidationError('The difference between {} and {} should not be greater than 1 month'.format(field1, field2))
    
    

class EmailReportForm(forms.ModelForm):
    class CronType(Enum):
        """Enum for different cron expression types."""
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"
        WORKINGDAYS = "workingdays"
    required_css_class = 'required'
    WORKINGDAYS_CHOICES = ScheduleReport.WORKINGDAYS
    frequencytypes = [
        ('workingdays', 'Working Days'),
        ('somethingelse', 'Something Else')
    ]

    
    cc            = forms.MultipleChoiceField(label='Email-CC', required=False, widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    to_addr       = forms.MultipleChoiceField(label="Email-To", required=False, widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    cronstrue     = forms.CharField(widget=forms.Textarea(attrs={'readonly':True, 'rows':2}), required=False)
    frequencytype = forms.ChoiceField(label="Frequency Type", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), choices=frequencytypes, required=False)
    workingdays   = forms.ChoiceField(label="Working Days", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),choices=WORKINGDAYS_CHOICES, required=False)
    workingperiod = forms.TimeField(label="Period", required=False)
    
    class Meta:
        fields = ['report_type', 'report_name', 'cron', 'report_sendtime',
                  'enable', 'ctzoffset', 'to_addr', 'cc', 'crontype', 'workingdays']
        model = ScheduleReport
        labels = {
            'cron':'Scheduler'
        }
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['cc'].choices = pm.People.objects.filter(isverified=True, client_id = self.S['client_id']).values_list('email', 'peoplename')
        self.fields['to_addr'].choices = pm.People.objects.filter(isverified=True, client_id = self.S['client_id']).values_list('email', 'peoplename')

        utils.initailize_form_fields(self)
    
    def clean(self):
        cd = super().clean()
        cd.update({'crontype':self.cron_type(cd['cron'])})
        return cd
    


    def cron_type(self, cron_expr):
        fields = cron_expr.split()
        if len(fields) != 5:
            return self.CronType.UNKNOWN.value

        # Check for daily cron expressions
        if all(field == "*" for field in fields[2:]):
            return self.CronType.DAILY.value

        # Revised check for weekly cron expressions
        elif fields[2] == "*" and fields[3] == "*" and fields[4] in map(str, range(0, 8)):
            return self.CronType.WEEKLY.value

        # Revised check for monthly cron expressions
        elif fields[2] in map(str, range(1, 32)) and fields[3] == "*" and fields[4] == "*":
            return self.CronType.MONTHLY.value

        # Otherwise, return unknown
        else:
            return self.CronType.WORKINGDAYS.value
    

class GeneratePDFForm(forms.ModelForm):
    required_css_class = "required"
    class Meta:
        model = GeneratePDF
        fields = ["additional_filter","customer","site","period_from","company","document_type","is_page_required","type_of_form"] #period_to & number_of_period

    # data fields
    customer              = forms.ChoiceField(label='Customer', required=True)
    site                  = forms.ChoiceField(label='Site', required=True) 
    period_from           = forms.MultipleChoiceField(label="Period", widget=s2forms.Select2MultipleWidget(attrs={
        'data-theme':'boostrap5'
    }), required=True)
    # period_to           = forms.ChoiceField(label='Period To', required=True)
    is_page_required = forms.BooleanField(
        label="Include Only Highlighted Page", 
        required=True, 
        initial=True, 
        help_text="Check this box to include only the highlighted page, excluding all unhighlighted pages."
    )
    pf_code_no = forms.CharField(label='PF Code No.', required=True)
    esic_code_no = forms.CharField(label='ESIC Code No.', required=True)
    ticket_no = forms.CharField(label='Ticket No.', required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.fields['customer'].initial:
            self.fields['customer'].required = False
        if not self.fields['site'].initial:
            self.fields['site'].required = False
        if not self.fields['period_from'].initial:
            self.fields['period_from'].required = False
        if not self.fields['is_page_required'].initial:
            self.fields['is_page_required'].required = False
        # if not self.fields['period_to'].initial:
        #     self.fields['period_to'].required = False
        utils.initailize_form_fields(self)