import django_select2.forms as s2forms
from django import forms
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import QueryDict
import re
from apps.activity.models.location_model import Location

import apps.onboarding.models as om
from apps.core import utils



class LocationForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_loccode'  : 'Spaces are not allowed in [Code]',
        'invalid_loccode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_loccode3' : "[Invalid code] Code should not end with '.' ",
        'invalid_latlng'   : "Please enter a correct GPS coordinate format (lat,lng)",
    }

    class Meta:
        model = Location
        fields = [
            'loccode', 'locname',  'parent', 'enable', 'type',
            'iscritical',  'ctzoffset', 'locstatus'
        ]
        labels = {
            'loccode':'Code', 'locname':'Name', 'parent':'Belongs To', 
        }

        # widgets = {
        #     'type':s2forms.Select2Widget(attrs={'class':'form-control'}),
        #     'locstatus':s2forms.Select2Widget(attrs={'class':'form-control'}),
        #     'parent':s2forms.Select2Widget(attrs={'class':'form-control'})
        # }

        # locastatus = forms.CharField(
        #     widget=forms.Select(
        #         attrs={'class':'form-control'}
        #     )
        # )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', False)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['loccode'].widget.attrs = {'style':"text-transform:uppercase"}
        #filters for dropdown fields
        self.fields['parent'].queryset = Location.objects.filter(client_id = S['client_id'], bu_id = S['bu_id'])
        self.fields['type'].queryset = om.TypeAssist.objects.filter(client_id = S['client_id'], tatype__tacode = 'LOCATIONTYPE')
        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        gpslocation = self.data.get('gpslocation', None)
        self.cleaned_data['gpslocation'] = None  # Default value if gpslocation is missing
        if gpslocation:
            data = QueryDict(self.request.POST.get('formData', ''))
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        loccode = self.data.get('loccode')
        if loccode:
            import re
            regex = "^[a-zA-Z0-9\\-_()#)]*$"
            if " " in loccode:
                raise forms.ValidationError(self.error_msg['invalid_loccode'])
            if not re.match(regex, loccode):
                raise forms.ValidationError(self.error_msg['invalid_loccode2'])
            if loccode.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_loccode3'])
            if loccode == getattr(self.cleaned_data.get('parent', None), 'loccode', None):
                raise forms.ValidationError("Code and Belongs To cannot be the same!")
            if not self.instance.id and Location.objects.filter(
                loccode=loccode,
                client_id=self.request.session.get('client_id'),
                bu_id=self.request.session.get('bu_id')
            ).exists():
                raise forms.ValidationError("Location code already exists, choose a different code.")
            self.cleaned_data['loccode'] = loccode.upper()
        return self.cleaned_data

    def clean_gpslocation(self, val):
        if gps := val:
            if gps == 'NONE': return GEOSGeometry(f'SRID=4326;POINT({0.0} {0.0})')
            regex = r'^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            gps = gps.replace('(', '').replace(')', '')
            if not re.match(regex, gps):
               raise forms.ValidationError(self.error_msg['invalid_latlng'])
            gps.replace(' ', '')
            lat, lng = gps.split(',')
            gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return gps
    
    def clean_loccode(self):
        if val:= self.cleaned_data['loccode']:
            if not self.instance.id and Location.objects.filter(loccode = val, client_id=self.request.session['client_id']).exists():
                raise forms.ValidationError("Location code already exist, choose different code")
            if ' ' in val:
                raise forms.ValidationError("Spaces are not allowed")
        return val.upper() if val else val
    
    def check_nones(self, cd):
        fields = {'parent': 'get_or_create_none_location',
                'type': 'get_none_typeassist',
                }
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
        
       