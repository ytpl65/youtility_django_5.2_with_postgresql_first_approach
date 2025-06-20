import django_select2.forms as s2forms
from django import forms
from apps.activity.models.job_model import Job, Jobneed
from apps.activity.models.asset_model import Asset
from apps.activity.models.question_model import QuestionSet
import apps.onboarding.models as om
import apps.peoples.models as pm
from apps.core import utils




class JobForm(forms.ModelForm):

    DURATION_CHOICES = [
        ('MIN', 'Minutes'),
        ('HRS', 'Hours'),
        ('WEEK', 'Week'),
        ('DAY', 'Day'), ]

    freq_duration = forms.ChoiceField(
        choices = DURATION_CHOICES, required = False, initial='MIN', widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    freq_duration2 = forms.ChoiceField(
        choices = DURATION_CHOICES, required = False, initial='MIN', widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    jobdesc = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}), label='Description', required=False)
    cronstrue = forms.CharField(widget=forms.Textarea(attrs={'readonly':True, 'rows':2}), required=False) 

    class Meta:
        model = Job
        fields = [
            'jobname', 'jobdesc', 'fromdate', 'uptodate', 'cron','sgroup',
            'identifier', 'planduration', 'gracetime', 'expirytime',
            'asset', 'priority', 'qset', 'pgroup', 'geofence', 'parent',
            'seqno', 'client', 'bu', 'starttime', 'endtime', 'ctzoffset',
            'frequency',  'scantype', 'ticketcategory', 'people', 'shift']

        labels = {
            'jobname'   : 'Name',            'fromdate'      : 'Valid From',
            'uptodate' : 'Valid To',     'cron'        : 'Scheduler', 'ticketcategory': 'Notify Catgory',
            'grace_time': 'Grace Time',   'planduration': 'Plan Duration',   'scan_type'      : 'Scan Type',
            'priority'  : 'Priority',     'people'    : 'People',          'pgroup'        : 'Group',          
            'qset_id'   : 'Question Set', 'shift'       : "Shift",           'asset'        : 'Asset',
        }

        widgets = {
            'ticketcategory': s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'scantype'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'shift'         : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'pgroup'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'asset'         : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'priority'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'fromdate'      : forms.DateTimeInput,
            'uptodate'      : forms.DateTimeInput,
            'ctzoffset'     : forms.NumberInput(attrs={"style": "display:none;"}),
            'qset'          : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'people'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'bu'            : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'cron'          :forms.TextInput(attrs={'style':'display:none'}),
            'jobdesc'       :forms.Textarea(attrs={'rows':'5', 'placeholder':"What does this tour about?"})
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_from_date(self):
        if val := self.cleaned_data.get('fromdate'):
            return self._extracted_from_clean_upto_date_3(val)

    def clean_upto_date(self):
        if val := self.cleaned_data.get('uptodate'):
            return self._extracted_from_clean_upto_date_3(val)

    # TODO Rename this here and in `clean_from_date` and `clean_upto_date`
    @staticmethod
    def _extracted_from_clean_upto_date_3(val):
        val = utils.to_utc(val)
        return val

    @staticmethod
    def clean_slno():
        return -1

    def clean(self):
        cd = super().clean()
        self.instance.jobdesc = f'{cd.get("bu")} - {cd.get("jobname")}'

class JobNeedForm(forms.ModelForm):
    class Meta:
        model = Jobneed
        fields = ['identifier', 'frequency', 'parent', 'jobdesc', 'asset', 'ticketcategory',
                  'qset',  'people', 'pgroup', 'priority', 'scantype', 'multifactor',
                  'jobstatus', 'plandatetime', 'expirydatetime', 'gracetime', 'starttime',
                  'endtime', 'performedby', 'gpslocation', 'cuser', 'remarks', 'ctzoffset',
                  'remarkstype']
        widgets = {
            'ticketcategory': s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'scantype'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'pgroup'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'people'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'qset'          : s2forms.ModelSelect2Widget(model = QuestionSet, search_fields = ['qset_name__icontains']),
            'asset'         : s2forms.ModelSelect2Widget(model = Asset, search_fields = ['assetname__icontains']),
            'priority'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'jobdesc'       : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'remarks'       : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'jobstatus'     : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'performedby'   : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'gpslocation'   : forms.TextInput,
            'remarks_type' : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'})

        }
        label = {
            'endtime': 'End Time',
            'ticketcategory':"Notify Category"
        }

class AdhocTaskForm(JobNeedForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    class Meta(JobNeedForm.Meta):
        labels = {
            'asset': 'Asset/SmartPlace',
            'starttime': 'Start Time',
            'plandatetime': 'Plan DateTime',
            'expirydatetime': 'Expity DateTime',
            'endtime': 'End Time',
            'gracetime': 'Grace Time',
            'jobstatus': 'Task Status',
            'scantype': 'ScanType',
            'gpslocation': 'GPS Location',
            'ticketcategory': 'Notify Category',
            'performedby': 'Performed By',
            'people': 'People',
            'qset': 'Question Set',
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        from django.conf import settings
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['gpslocation'].required  = False
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        utils.initailize_form_fields(self)

class PPMForm(forms.ModelForm):
    timeInChoices      = [('MINS', 'Minute'),('HRS', 'Hour'), ('DAYS', 'Day'), ('WEEKS', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    FREQUENCY_CHOICES   = [('WEEKLY', 'Weekly'),('FORTNIGHTLY', 'Fortnight'), ('BIMONTHLY', 'Bimonthly'),
                           ("QUARTERLY", "Quarterly"), ('MONTHLY', 'Monthly'),('HALFYEARLY', 'Half Yearly'),
                           ('YEARLY', 'Yearly')]
    
    planduration_type  = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    gracetime_type     = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    expirytime_type    = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES, label="Frequency", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    cronstrue = forms.CharField(widget=forms.Textarea(attrs={'readonly':True, 'rows':2}), required=False) 

    required_css_class = "required"


    class Meta:
        model = Job
        fields = [
            'jobname', 'jobdesc', 'planduration', 'gracetime', 'expirytime', 'cron', 'priority', 'ticketcategory',
            'fromdate', 'uptodate', 'people', 'pgroup', 'scantype', 'frequency', 'asset', 'qset', 'assign_to',
            'ctzoffset', 'parent', 'identifier', 'seqno'
        ]
        labels = {
            'asset':'Asset', 'qset':"Question Set", 'people':"People", 
            'scantype':'Scantype', 'priority':'Priority',
            'jobdesc':'Description', 'jobname':"Name", 'planduration':"Plan Duration",
            'expirytime':'Exp time', 'cron':"Scheduler", 'ticketcategory':'Notify Category',
            'fromdate':'Valid From', 'uptdate':'Valid To', 'pgroup':'Group', 
            'assign_to':'Assign to'
        }
        widgets = {
            'asset'         : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'qset'          : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'people'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'pgroup'        : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'priority'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'scantype'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'ticketcategory': s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'identifier':forms.TextInput(attrs={'style':"display:none;"})
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        
        self.fields['asset'].required = True
        self.fields['qset'].required = True
        self.fields['identifier'].initial = 'PPM'
        self.fields['identifier'].widget.attrs = {'style':"display:none"}
        
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['qset'].queryset = QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['asset'].queryset = Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET', 'CHECKPOINT'], sitewise=True)
        utils.initailize_form_fields(self)
    
    def clean(self):
        cd          = self.cleaned_data
        times_names = ['planduration', 'expirytime', 'gracetime']
        types_names = ['planduration_type', 'expirytime_type', 'gracetime_type']
        
        
        times = [cd.get(time) for time in times_names]
        types = [cd.get(type) for type in types_names]
        for time, type, name in zip(times, types, times_names):
            cd[name] = self.convertto_mins(type, time)
        self.cleaned_data = self.check_nones(cd)

            
    
    def check_nones(self, cd):
        fields = {
            'parent':'get_or_create_none_job',
            'people': 'get_or_create_none_people',
            'pgroup': 'get_or_create_none_pgroup',
            'asset' : 'get_or_create_none_asset'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd      
    
    @staticmethod
    def convertto_mins(_type, _time):
        if _type == 'HRS':
            return _time * 60
        if _type == 'WEEKS':
            return _time *7 * 24 * 60
        return _time * 24 * 60 if _type == 'DAYS' else _time

class PPMFormJobneed(forms.ModelForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    required_css_class = "required"


    class Meta:
        model = Jobneed
        fields = [
            'jobdesc', 'asset',  'priority', 'ticketcategory', 'gracetime','starttime', 'endtime',
            'performedby','expirydatetime', 'people', 'pgroup', 'scantype', 'jobstatus',  'qset', 'assign_to',
            'plandatetime', 'ctzoffset'
        ]
        labels = {
            'asset':'Asset', 'qset':"Question Set", 'people':"People", 
            'scantype':'Scantype', 'priority':'Priority',
            'jobdesc':'Description', 'ticketcategory':'Notify Category',
            'fromdate':'Valid From', 'uptdate':'Valid To', 'pgroup':'Group', 
            'assign_to':'Assign to'
        }
        widgets = {
            'asset'         : s2forms.Select2Widget,
            'qset'          : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'priority'      : s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'ticketcategory': s2forms.Select2Widget,
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['qset'].queryset = QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['asset'].queryset = Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET'], sitewise=True)
        utils.initailize_form_fields(self)
 