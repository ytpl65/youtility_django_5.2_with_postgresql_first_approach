# from standard library

# from django core
from django import forms
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _
from apps.core import utils
# from thirdparty apps and packages
from django_select2 import forms as s2forms
from django.conf import settings
import json

# from this project
import apps.onboarding.models as obm # onboarding-models
from apps.peoples import models as pm # onboarding-utils
from django.contrib.gis.geos import GEOSGeometry
from django.http import QueryDict
from apps.peoples.utils import create_caps_choices_for_clientform
import re
#========================================= BEGIN MODEL FORMS ======================================#

class SuperTypeAssistForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "(Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    class Meta:
        model  = obm.TypeAssist
        fields = ['tacode' , 'taname', 'tatype', 'ctzoffset', 'enable']
        labels = {
                'tacode': 'Code',
                'taname': 'Name',
                'tatype': 'Type',
                'enable':'Enable'}

        widgets = {
            'tatype':s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'tacode':forms.TextInput(attrs={'placeholder': 'Enter code without space and special characters', 'style': "text-transform: uppercase;"}),
            'taname':forms.TextInput(attrs={'placeholder': "Enter name"}),
            }

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        super(SuperTypeAssistForm, self).__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['enable'].initial = True

    def is_valid(self) -> bool:

        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_tatype(self):
        return self.cleaned_data.get('tatype')

    def clean_tacode(self):
        value = self.cleaned_data.get('tacode')
        regex = "^[a-zA-Z0-9\-_()#]*$"
        if " " in value: raise forms.ValidationError(self.error_msg['invalid_code'])
        if  not re.match(regex, value):
            raise forms.ValidationError(self.error_msg['invalid_code2'])
        if value.endswith('.'):
            raise forms.ValidationError(self.error_msg['invalid_code3'])
        return value.upper()

class TypeAssistForm(SuperTypeAssistForm): 
    required_css_class = "required"

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['enable'].initial = True
        self.fields['tatype'].queryset = obm.TypeAssist.objects.filter((Q(cuser__is_superuser = True) | Q(client_id__in =  [S['client_id'], 1])), enable=True )
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result
    
    def clean(self):
        super().clean()

    def clean_tacode(self):
        super().clean_tacode()
        if val:= self.cleaned_data.get('tacode'):
            val = val.upper()
            if len(val)>25: raise forms.ValidationError("Max Length reached!!")
        return val



class BtForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_bucode'  : 'Spaces are not allowed in [Code]',
        'invalid_bucode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_bucode3' : "[Invalid code] Code should not endwith '.' ",
        'invalid_latlng'  : "Please enter a correct gps coordinates.",
        'invalid_permissibledistance':"Please enter a correct value for Permissible Distance",
        'invalid_solid': "Please enter a correct value for Sol id",
        'invalid_name'  : "[Invalid text] Only these special characters [-, _, @, #, . , &] are allowed in name field",                   
    }
    parent = forms.ModelChoiceField(label='Belongs to', required = False, queryset = obm.Bt.objects.all())
    controlroom = forms.MultipleChoiceField(required=False, label='Control Room')
    permissibledistance = forms.IntegerField(required=False, label='Permissible Distance')
    address = forms.CharField(required=False, label='Address', max_length=500)
    total_people_count = forms.IntegerField(required=False, min_value=0,label='Total People Count')
    designation = forms.ModelChoiceField(label='Desigantion',required=False, queryset = obm.TypeAssist.objects.filter(tatype__tacode='DESIGNATION',enable = True))
    designation_count = forms.IntegerField(required=False, min_value=0,label='Designation Count')
    posted_people = forms.MultipleChoiceField(
    label='Posted People',
    required=False,
    widget=s2forms.Select2MultipleWidget(attrs={
        'class': 'form-select form-select-solid',
        'data-placeholder': 'Select Posted People',
        'data-theme': 'bootstrap5'
    })
)
    jsonData = forms.CharField(widget=forms.HiddenInput(), required=False)
    class Meta:
        model  = obm.Bt
        fields = ['bucode', 'buname', 'parent', 'butype', 'identifier', 'siteincharge',
                'iswarehouse', 'isserviceprovider', 'isvendor', 'enable', 'ctzoffset',
                'gpsenable', 'skipsiteaudit', 'enablesleepingguard', 'deviceevent', 'solid']

        labels = {
            'bucode'             : 'Code',
            'buname'             : 'Name',
            'butype'             : 'Site Type',
            'identifier'         : 'Type',
            'iswarehouse'        : 'Warehouse',
            'isenable'           : 'Enable',
            'isvendor'           : 'Vendor',
            'isserviceprovider'  : 'Service Provider',
            'gpsenable'          : 'GPS Enable', 
            'skipsiteaudit'      : 'Skip Site Audit',
            'enablesleepingguard': 'Enable Sleeping Guard',
            'deviceevent'        : 'Device Event Log',
            'solid'              : 'Sol Id',
            'siteincharge'       :'Site Manager'   
        }

        widgets = { 
            'bucode'      : forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'}),
            'buname'      : forms.TextInput(attrs={'placeholder': 'Name'}),
            }    

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.client = kwargs.pop('client', False)
        self.request = kwargs.pop('request', False)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['parent'].widget = s2forms.Select2Widget(attrs={'class': 'form-select form-select-solid','data-placeholder': 'Select an option','data-theme': 'bootstrap5'})
        self.fields['controlroom'].widget = s2forms.Select2MultipleWidget(attrs={'class': 'form-select form-select-solid','data-placeholder': 'Select an option','data-theme': 'bootstrap5'})
        self.fields['address'].widget = forms.Textarea(attrs={'rows': 2, 'cols': 15})
        self.fields['designation'].widget = s2forms.Select2Widget(attrs={'class': 'form-select form-select-solid','data-placeholder': 'Select an option','data-theme': 'bootstrap5'})
        self.fields['identifier'].widget = s2forms.Select2Widget(attrs={'class':'form-select form-select-solid','data-placeholder':'Select an option','data-theme':'bootstrap5'})
        self.fields['butype'].widget = s2forms.Select2Widget(attrs={'data-placeholder':'Select an Option','class':'form-select-solid','data-theme':'bootstrap5'})


        if self.client:
            self.fields['identifier'].initial = obm.TypeAssist.objects.get(tacode='CLIENT').id
            self.fields['identifier'].required= True
        
        self.fields['siteincharge'].initial = 1
        #filters for dropdown fields
        self.fields['identifier'].queryset = obm.TypeAssist.objects.filter(Q(tacode='CLIENT') if self.client else Q(tatype__tacode="BVIDENTIFIER"))
        self.fields['butype'].queryset = obm.TypeAssist.objects.filter(tatype__tacode="SITETYPE", client_id = S['client_id'])
        qset = obm.Bt.objects.get_whole_tree(self.request.session['client_id'])
        self.fields['parent'].queryset = obm.Bt.objects.filter(id__in = qset)
        self.fields['controlroom'].choices = pm.People.objects.controlroomchoices(self.request)
        self.fields['posted_people'].choices = pm.People.objects.get_people_for_posted_ppl_on_bu(self.request)
        self.fields['siteincharge'].queryset = pm.People.objects.filter(Q(peoplecode ='NONE') | (Q(client_id = self.request.session['client_id']) & Q(enable=True)))
        self.fields['designation'].queryset = obm.TypeAssist.objects.filter(Q(bu_id__in=[S['bu_id'], 1]) | Q(bu_id__in=S['assignedsites']) | Q(bu_id__isnull=True),Q(client_id__in=[S['client_id'], 1]),Q(tatype__tacode='DESIGNATION'))        
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result


    def clean(self):
        super().clean()
        
        from .utils import create_bv_reportting_heirarchy
        newcode  = self.cleaned_data.get('bucode')
        newtype  = self.cleaned_data.get('identifier')
        parent   = self.cleaned_data.get('parent')
        instance = self.instance
        if newcode and newtype and instance:
            create_bv_reportting_heirarchy(instance, newcode, newtype, parent)
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if self.request.POST.get('jsonData'):
            json_data = self.request.POST.get('jsonData')
            self.cleaned_data['jsonData'] = json.loads(json_data)
        return self.cleaned_data

    def clean_bucode(self):
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if value := self.cleaned_data.get('bucode'):
            regex = "^[a-zA-Z0-9\-_#()]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_bucode'])
            if  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_bucode2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_bucode3'])
            return value.upper()

    def clean_gpslocation(self, val):
        if gps := val:
            if gps == 'NONE': return GEOSGeometry(f'SRID=4326;POINT({0.0} {0.0})')
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            gps = gps.replace('(', '').replace(')', '')
            if not re.match(regex, gps):
               raise forms.ValidationError(self.error_msg['invalid_latlng'])
            gps.replace(' ', '')
            lat, lng = gps.split(',')
            gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return gps
    
    def clean_permissibledistance(self):
        if val := self.cleaned_data.get('permissibledistance'):
            regex = "^[0-9]*$"
            if not re.match(regex, str(val)):
                raise forms.ValidationError(self.error_msg['invalid_permissibledistance'])
            if val < 0:
                raise forms.ValidationError(self.error_msg['invalid_permissibledistance'])
        return val

    def clean_solid(self):
        if val:=self.cleaned_data.get('solid'):
            regex = "^[a-zA-Z0-9]*$"
            if not re.match(regex, str(val)):
                raise forms.ValidationError(self.error_msg['invalid_solid'])
        return val
    
    def clean_buname(self):
        if value := self.cleaned_data.get('buname'):
            regex = r"^[a-zA-Z0-9\-_@#.,\(\|\)& ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_name'])
        return value



class ShiftForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
        'max_hrs_exceed': "Maximum hours in a shift cannot be greater than 12hrs",
        "min_hrs_required": "Minimum hours of a shift should be greater than 4hrs",
        "invalid_overtime": "Overtime hours cannot exceed regular shift duration"
    }
    shiftduration = forms.CharField(widget = forms.TextInput(attrs={'readonly':True}), label="Duration", required = False)
    overtime = forms.IntegerField(required=False, min_value=0, label="Overtime (hours)", 
                                widget=forms.NumberInput(attrs={'placeholder': "Enter overtime hours"}))
    peoplecount = forms.IntegerField(required=True, min_value=1, label="People Count", 
                                 widget=forms.NumberInput(attrs={'placeholder': "Enter people count"}))

    class Meta:
        model = obm.Shift
        fields = ['shiftname', 'starttime', 'endtime', 'ctzoffset',
        'nightshiftappicable', 'shiftduration', 'designation', 'captchafreq', 'peoplecount','shift_data','overtime' ]
        labels={
            'shiftname'  : 'Shift Name',
            'starttime'  : 'Start Time',
            'endtime'    : 'End Time',
            'captchafreq': 'Captcha Frequency',
            'designation': "Designation",
            'peoplecount': "People Count",
            'shift_data' : "Shift Data",
            'overtime'   :"Overtime Hours"
        }
        widgets ={
            'shiftname':forms.TextInput(attrs={'placeholder': "Enter shift name"}),
            'nightshiftappicable':forms.CheckboxInput(attrs={'onclick': "return false"}),
            'designation': s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'overtime': forms.NumberInput(attrs={'class': 'form-control'})
        }

    def clean_overtime(self):
        overtime = self.cleaned_data.get('overtime')
        shiftduration = self.cleaned_data.get('shiftduration')
        
        if overtime and shiftduration:
            if overtime > (shiftduration / 60):  # Convert minutes to hours
                raise forms.ValidationError(self.error_msg['invalid_overtime'])
        return overtime

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['nightshiftappicable'].initial = False 
        self.fields['designation'].queryset = obm.TypeAssist.objects.filter(Q(bu_id__in=[S['bu_id'], 1]) | Q(bu_id__in=S['assignedsites']) | Q(bu_id__isnull=True),Q(client_id__in=[S['client_id'], 1]),Q(tatype__tacode='DESIGNATION'))
        self.fields['designation'].widget = forms.Select(
            choices=[
                (item.tacode, item.taname)  # (value, label)
                for item in self.fields['designation'].queryset
            ]
        )
        utils.initailize_form_fields(self)

    def clean_shiftname(self):
        if val := self.cleaned_data.get('shiftname'):
            return val

    def clean_shiftduration(self):
        if val := self.cleaned_data.get('shiftduration'):
            h, m = val.split(',')
            hrs = int(h.replace("Hrs", ""))
            mins = int(m.replace("min", ""))
            if hrs > 12:
                raise forms.ValidationError(self.error_msg['max_hrs_exceed'])
            if hrs < 5:
                raise forms.ValidationError(self.error_msg['min_hrs_required'])
            return hrs*60+mins

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result



class GeoFenceForm(forms.ModelForm):
    required_css_class = 'required'
    class Meta:
        model = obm.GeofenceMaster
        fields = ['gfcode', 'gfname', 'alerttopeople', 'bu',
                  'alerttogroup', 'alerttext', 'enable', 'ctzoffset']
        labels = {
            'gfcode': 'Code', 'gfname': 'Name', 'alerttopeople': 'Alert to People',
            'alerttogroup': 'Alert to Group', 'alerttext': 'Alert Text'
        }
        widgets = {
            'gfcode':forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'})
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['alerttogroup'].required = True
        self.fields['bu'].queryset = obm.Bt.objects.filter(id__in = self.request.session['assignedsites'])
        self.fields['alerttopeople'].required = True
        self.fields['alerttext'].required = True
        self.fields['bu'].required = False
        utils.initailize_form_fields(self)

    def clean_gfcode(self):
        return val.upper() if (val := self.cleaned_data.get('gfcode')) else val
#========================================== END MODEL FORMS =======================================#

#========================================== START JSON FORMS =======================================#
class BuPrefForm(forms.Form):
    required_css_class = "required"

    mobilecapability         = forms.MultipleChoiceField(required = False, label="Mobile Capability", widget = s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    webcapability            = forms.MultipleChoiceField(required = False, label="Web Capability", widget = s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    reportcapability         = forms.MultipleChoiceField(required = False, label="Report Capability", widget = s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    portletcapability        = forms.MultipleChoiceField(required = False, label="Portlet Capability", widget = s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    validimei                = forms.CharField(max_length = 15, required = False,label="IMEI No.")
    validip                  = forms.CharField(max_length = 15, required = False, label="IP Address")
    usereliver               = forms.BooleanField(initial = False, required = False, label="Reliver needed?")
    malestrength             = forms.IntegerField(initial = 0, label="Male Strength")
    femalestrength           = forms.IntegerField(initial = 0, label="Female Strength")
    reliveronpeoplecount     = forms.IntegerField(initial = 0, label="Reliver On People Count", required=False)
    pvideolength             = forms.IntegerField(initial="10", label='Panic Video Length (sec)')
    guardstrenth             = forms.IntegerField(initial = 0)
    siteclosetime            = forms.TimeField(label="Site Close Time", required = False)
    tag                      = forms.CharField(max_length = 200, required = False)
    siteopentime             = forms.TimeField(required = False, label="Site Open Time")
    nearby_emergencycontacts = forms.CharField(max_length = 500, required = False)
    ispermitneeded           = forms.BooleanField(initial = False, required=False)



    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

class ClentForm(BuPrefForm):
    BILLINGTYPES = [
        ('', ""),
        ('SITEBASED', 'Site Based'),
        ('LICENSEBASED', 'Liscence Based'),
        ('USERBASED', 'User Based'),
    ]
    femalestrength = None
    guardstrenth = None
    malestrength = None
    startdate = forms.DateField(label='Start Date', required=True, input_formats=settings.DATE_INPUT_FORMATS, widget=forms.DateInput)
    enddate = forms.DateField(label='End Date', required=True, input_formats=settings.DATE_INPUT_FORMATS, widget=forms.DateInput)
    onstop = forms.BooleanField(label='On Stop', required=False, initial=False)
    onstopmessage = forms.CharField(widget=forms.Textarea(attrs={'rows':1}),label='On Stop Message', required=False)
    clienttimezone = forms.ChoiceField(label="Time Zone", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), choices=utils.generate_timezone_choices, required=False)
    billingtype = forms.ChoiceField(label="Billing Type", widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}), choices=BILLINGTYPES, initial='SITEBASED', required=True)
    no_of_devices_allowed = forms.IntegerField(label="No of Devices Allowed", required=False, initial=0)
    devices_currently_added = forms.IntegerField(label="No of Devices Currently Added", required=False, initial=0)
    no_of_users_allowed_mob = forms.IntegerField(label="No of Users Allowed For Mobile", required=False, initial=0)
    no_of_users_allowed_web = forms.IntegerField(label="No of Users Allowed For Web", required=False, initial=0)
    no_of_users_allowed_both = forms.IntegerField(label="No of Users Allowed For Both", required=False, initial=0)
    

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        web, mob, portlet, report = create_caps_choices_for_clientform()
        self.fields['webcapability'].choices = web
        self.fields['mobilecapability'].choices = mob
        self.fields['reportcapability'].choices = report
        self.fields['portletcapability'].choices = portlet
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('mobilecapability') and not cleaned_data.get('webcapability'):
            msg = "Please select atleast one capability"
            self.add_error("mobilecapability", msg)
            self.add_error("webcapability", msg)
        #if usereliver is checked then reliveronpeoplecount should be greater than 0
        if cleaned_data.get('usereliver') and cleaned_data.get('reliveronpeoplecount') <= 0:
            self.add_error('reliveronpeoplecount', "Reliver on people count should be greater than 0")
            
    
    
    
    def clean_validip(self):
        if val := self.cleaned_data.get('validip'):
            #check if ip is valid
            text = val.split('.')
            if len(text) != 4:
                raise forms.ValidationError("Invalid IP Address")
        return val
    
    def clean_validimei(self):
        if val := self.cleaned_data.get('validimei'):
            #check if imei is valid
            if  not utils.isValidEMEI(val):
                raise forms.ValidationError("Invalid IMEI No.")
        return val

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

#========================================== END JSON FORMS =======================================#

class ImportForm(forms.Form):
    TABLECHOICES = [
        ('TYPEASSIST', 'User Defined Types'),
        ('BU', 'Business Unit'),
        ('LOCATION', 'Location'),
        ('ASSET', 'Asset'),
        ('VENDOR', 'Vendor'),
        ('PEOPLE', 'People'),
        ('QUESTION', 'Question'),
        ('QUESTIONSET', 'Question Set'),
        ('QUESTIONSETBELONGING', 'Question Set Belonging'),
        ('GROUP', 'Group'),
        ('GROUPBELONGING', 'Group Belongings'),
        ('SCHEDULEDTASKS', 'Scheduled Tasks'),
        ('SCHEDULEDTOURS', 'Scheduled Tours'),
        ('GEOFENCE', 'Geofence'),
        ('GEOFENCE_PEOPLE', 'Geofence People'),
        ('SHIFT', 'Shift'),
        ('BULKIMPORTIMAGE','Bulk Import Image')
    ]
    table = forms.ChoiceField(
        choices=TABLECHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    importfile = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    #importfile = forms.FileField(required = True, label='Import File', max_length = 50, allow_empty_file = False)
    ctzoffset = forms.IntegerField()
    #table = forms.ChoiceField(required = True, choices = TABLECHOICES, label='Select Type of Data', initial='TYPEASSISTS', widget=s2forms.Select2Widget)

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

class ImportFormUpdate(forms.Form):
    TABLECHOICES = [
        ('TYPEASSIST', 'User Defined Types'),
        ('BU', 'Business Unit'),
        ('LOCATION', 'Location'),
        ('ASSET', 'Asset'),
        ('VENDOR', 'Vendor'),
        ('PEOPLE', 'People'),
        ('QUESTION', 'Question'),
        ('QUESTIONSET', 'Question Set'),
        ('QUESTIONSETBELONGING', 'Question Set Belonging'),
        ('GROUP', 'Group'),
        ('GROUPBELONGING', 'Group Belongings'),
        ('SCHEDULEDTASKS', 'Scheduled Tasks'),
        ('SCHEDULEDTOURS', 'Scheduled Tours'),
    ]
    importfile = forms.FileField(required = True, label='Import File', max_length = 50, allow_empty_file = False)
    ctzoffset = forms.IntegerField()
    table = forms.ChoiceField(required = True, choices = TABLECHOICES, label='Select Type of Data', initial='TYPEASSISTS', widget=s2forms.Select2Widget)

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
