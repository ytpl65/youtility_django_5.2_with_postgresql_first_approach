from django import forms
from django.contrib.gis.geos import GEOSGeometry
from django_select2 import forms as s2forms
from apps.core import utils
import apps.attendance.models as atdm
import apps.peoples.models as pm

class AttendanceForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = atdm.PeopleEventlog
        fields = ['people', 'datefor', 'ctzoffset', 'punchintime', 'punchouttime', 
         'peventtype', 'verifiedby', 'remarks', 'shift', 'facerecognitionin', 'facerecognitionout']
        labels = {
            'people'        : 'People',
            'punchintime'    : 'In Time',
            'punchouttime'   : 'Out Time',
            'datefor'         : 'For Date',
            'peventtype'      : 'Attendance Type',
            'verifiedby'      : 'Verified By',
            'facerecognition' : 'Enable FaceRecognition',
            'remarks'         : "Remark"}
        widgets = {
            'people'    : s2forms.ModelSelect2Widget(
                model     = pm.People, search_fields =  ['peoplename__icontains', 'peoplecode__icontains']
            ),
            'verifiedby'  : s2forms.ModelSelect2Widget(
                model     = pm.People, search_fields = ['peoplename__icontains', 'peoplecode__icontains']
            ),
            'shift'       : s2forms.Select2Widget,
            'peventtype'  : s2forms.Select2Widget,
            
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['datefor'].required       = True
        self.fields['punchintime'].required  = True
        self.fields['punchouttime'].required = True
        self.fields['verifiedby'].required    = True
        self.fields['people'].required        = True
        self.fields['peventtype'].required    = True
        self.fields['shift'].initial          = 1

    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result 

def clean_geometry(val):
    try:
        val = GEOSGeometry(val, srid = 4326)
    except ValueError as e:
        raise forms.ValidationError('lat lng string input unrecognized!') from e
    else: return val

class ConveyanceForm(forms.ModelForm):
    required_css_class = "required"
    transportmodes = forms.MultipleChoiceField(
        choices = atdm.PeopleEventlog.TransportMode.choices,
        required = True,
        widget = s2forms.Select2MultipleWidget,
        label='Transport Modes')
    
    class Meta:
        model = atdm.PeopleEventlog
        fields = ['people', 'transportmodes', 'expamt', 'duration', 'ctzoffset',
                  'distance', 'startlocation', 'endlocation', 'punchintime', 'punchouttime']
        widgets = {
            'startlocation':forms.TextInput(),
            'endlocation':forms.TextInput(),
            'transportmodes':s2forms.Select2MultipleWidget,
            'startlocation':forms.Textarea(attrs={'rows': 3, 'cols': 20}),
            'endlocation':forms.Textarea(attrs={'rows': 3, 'cols': 20}),}
        labels = {
            'expamt': 'Expense Amount',
            'transportmodes': 'Transport Modes',
            'startlocation': 'Start Location',
            'endlocation': 'End Location',
            'punchintime': 'Start Time',
            'punchouttime': 'End Time',
            'distance': 'Distance'}


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        for visible in self.visible_fields():
            if visible.name in ['startlocation', 'endlocation', 'expamt', 'transportmodes']:
                visible.required = False

    def clean(self):
        super(ConveyanceForm, self).clean()

    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_startlocation(self):
        if val := self.cleaned_data.get('startlocation'):
            val = clean_geometry(val)
        return val

    def clean_endlocation(self):
        if val := self.cleaned_data.get('endlocation'):
            val = clean_geometry(val)
        return val

    def clean_journeypath(self):
        if val := self.cleaned_data.get('journeypath'):
            val = clean_geometry(val)
        return val



class TrackingForm(forms.ModelForm):
    gpslocation = forms.CharField(max_length = 200, required = True)
    class Meta:
        model = atdm.Tracking
        fields = ['deviceid', 'gpslocation', 'receiveddate', 
                  'people', 'transportmode']

    def clean_gpslocation(self):
        if val := self.cleaned_data.get('gpslocation'):
            val = clean_geometry(val)
        return val

