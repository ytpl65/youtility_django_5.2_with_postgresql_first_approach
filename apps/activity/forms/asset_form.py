import re
from datetime import datetime
import django_select2.forms as s2forms
from django import forms
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from django.http import QueryDict
import apps.onboarding.models as om
from apps.core import utils

from apps.activity.models.asset_model import Asset
from apps.activity.models.location_model import Location

from apps.core.exceptions import ValidationError



class AssetForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_assetcode'  : 'Spaces are not allowed in [Code]',
        'invalid_assetcode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_assetcode3' : "[Invalid code] Code should not endwith '.' "
    }
    enable = forms.BooleanField(required=False, initial=True, label='Enable')
    status_field = forms.ChoiceField(choices=Asset.RunningStatus.choices, label = 'Duration of Selected Status', required=False)
    
    class Meta:
        model = Asset
        fields = [
            'assetcode', 'assetname', 'runningstatus', 'type', 'category', 
            'subcategory', 'brand', 'unit', 'capacity', 'servprov', 'parent',
            'iscritical', 'enable', 'identifier', 'ctzoffset','location'
        ]
        labels={
            'assetcode':'Code', 'assetname':'Name', 'runningstatus':'Status',
            'type':'Type', 'category':'Category', 'subcategory':'Sub Category',
            'brand':'Brand', 'unit':'Unit', 'capacity':'Capacity', 'servprov':'Service Provider',
            'parent':'Belongs To', 'gpslocation':'GPS', 'location':'Location'
        }
        widgets={
            'identifier':forms.TextInput(attrs={'style':"display:none;"})
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['enable'].widget.attrs = {'checked':False} if self.instance.id else {'checked':True}
        self.fields['assetcode'].widget.attrs = {'style':"text-transform:uppercase"}
        
        self.fields['identifier'].widget.attrs = {'style':"display:none"}
        self.fields['identifier'].initial      = 'ASSET'
        self.fields['capacity'].required       = False
        self.fields['servprov'].required       = False
        
        #filters for dropdown fields
        self.fields['parent'].queryset         = Asset.objects.filter(~Q(runningstatus='SCRAPPED'), identifier='ASSET', bu_id = S['bu_id'])
        self.fields['location'].queryset       = Location.objects.filter(~Q(locstatus='SCRAPPED'), bu_id = S['bu_id'])
        self.fields['type'].queryset           = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETTYPE', 'ASSET_TYPE']), client_id = S['client_id'])
        self.fields['category'].queryset       = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETCATEGORY', 'ASSET_CATEGORY']), client_id = S['client_id'])
        self.fields['subcategory'].queryset    = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETSUBCATEGORY', 'ASSET_SUBCATEGORY']), client_id = S['client_id'])
        self.fields['unit'].queryset           = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETUNIT', 'ASSET_UNIT', 'UNIT']), client_id = S['client_id'])
        self.fields['brand'].queryset          = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETBRAND', 'ASSET_BRAND', 'BRAND']), client_id = S['client_id'])
        self.fields['servprov'].queryset       = om.Bt.objects.filter(id = S['bu_id'], isserviceprovider = True, enable=True)
        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        gpslocation = self.data.get('gpslocation', None)
        self.cleaned_data['gpslocation'] = None  # Default value if gpslocation is missing
        if gpslocation:
            data = QueryDict(self.request.POST.get('formData', ''))
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if self.cleaned_data.get('parent') is None:
            self.cleaned_data['parent'] = utils.get_or_create_none_asset()
        assetcode = self.data.get('assetcode')
        if assetcode:
            import re
            regex = "^[a-zA-Z0-9\\-_()#)]*$"
            if " " in assetcode:
                raise forms.ValidationError(self.error_msg['invalid_assetcode'])
            if not re.match(regex, assetcode):
                raise forms.ValidationError(self.error_msg['invalid_assetcode2'])
            if assetcode.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_assetcode3'])
            if assetcode == getattr(self.cleaned_data.get('parent', None), 'assetcode', None):
                raise forms.ValidationError("Code and Belongs To cannot be the same!")
            if not self.instance.id and Asset.objects.filter(
                assetcode=assetcode,
                client_id=self.request.session.get('client_id'),
                bu_id=self.request.session.get('bu_id')
            ).exists():
                raise forms.ValidationError("Asset code already exists, choose a different code.")
            self.cleaned_data['assetcode'] = assetcode.upper()
        return self.cleaned_data
    

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
    
    def clean_assetcode(self):
        if val := self.cleaned_data.get('assetcode'):
            if not self.instance.id and  Asset.objects.filter(assetcode = val, client_id = self.request.session['client_id']).exists():
                raise forms.ValidationError("Asset with this code already exist")
            if ' ' in val:
                raise forms.ValidationError("Spaces are not allowed")
            return val.upper()
            
        return val
    
    def check_nones(self, cd):
        fields = {'parent': 'get_or_create_none_asset',
                'servprov': 'get_or_create_none_bv',
                'type': 'get_none_typeassist',
                'category': 'get_none_typeassist',
                'subcategory': 'get_none_typeassist',
                'brand': 'get_none_typeassist',
                'unit': 'get_none_typeassist',
                'location':'get_or_create_none_location'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd



class AssetExtrasForm(forms.Form):
    required_css_class = "required"
    ismeter =    forms.BooleanField(initial=False, required=False, label='Meter')
    is_nonengg_asset =    forms.BooleanField(initial=False, required=False, label='Non Engg. Asset')
    supplier      = forms.CharField(max_length=55, label='Supplier', required=False)
    meter         = forms.ChoiceField(label='Meter', required=False)
    invoice_no    = forms.CharField( max_length=55, required=False, label='Invoice No')
    invoice_date  = forms.DateField(required=False, label='Invoice Date')
    service       = forms.ChoiceField(label='Service', required=False)
    sfdate        = forms.DateField(label='Service From Date', required=False)
    stdate        = forms.DateField(label='Service To Date', required=False)
    yom           = forms.IntegerField(min_value=1980, max_value=utils.get_current_year(), label='Year of Manufactured', required=False)
    msn           = forms.CharField( max_length=55, required=False, label='Manufactured Serial No')
    bill_val      = forms.CharField(label='Bill Value', required=False, max_length=55)
    bill_date     = forms.DateField(label='Bill Date', required=False)
    purchase_date = forms.DateField(label='Purchase Date', required=False)
    inst_date     = forms.DateField(label='Installation Date', required=False)
    po_number     = forms.CharField(max_length=55, label='Purchase Order Number',required=False)
    far_asset_id  = forms.CharField(max_length=55, label='FAR Aseet ID',required=False)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['service'].choices = om.TypeAssist.objects.select_related('tatype').filter(client_id = S['client_id'], tatype__tacode__in = ['SERVICE_TYPE','ASSETSERVICE', 'ASSET_SERVICE' 'SERVICETYPE']).values_list('id', 'tacode')
        self.fields['meter'].choices = om.TypeAssist.objects.select_related('tatype').filter(client_id = S['client_id'], tatype__tacode__in = ['ASSETMETER', 'ASSET_METER']).values_list('id', 'tacode')  
        utils.initailize_form_fields(self)
    
    def clean(self):
        cd = super().clean()  # cleaned_data
        sfdate = cd.get('sfdate')
        stdate = cd.get('stdate')
        bill_date = cd.get('bill_date')
        purchase_date = cd.get('purchase_date')
        if sfdate and stdate and sfdate > stdate:
            raise forms.ValidationError('Service from date should be smaller than service to date!')
        if bill_date and bill_date > datetime.now().date():
            raise forms.ValidationError('Bill date cannot be greater than today')
        if purchase_date and purchase_date > datetime.now().date():
            raise forms.ValidationError('Purchase date cannot be greater than today')
        return cd


class  MasterAssetForm(forms.ModelForm):
    required_css_class = "required"
    SERVICE_CHOICES = [
        ('NONE', 'None'),
        ('AMC', 'AMC'),
        ('WARRANTY', 'Warranty'),
    ]
    

    tempcode       = forms.CharField(max_length = 100, label='Temporary Code', required = False)
    service        = forms.ChoiceField(choices = SERVICE_CHOICES, initial='NONE', required = False, label='Service')
    sfdate         = forms.DateField(required = False, label='Service From Date')
    stdate         = forms.DateField(required = False, label='Service To Datre')
    msn            = forms.CharField(required = False, max_length = 50,label='Manufacture Sr. No')
    yom            = forms.CharField(required = False, max_length = 50,label='Manufacture Date')
    bill_val       = forms.IntegerField(required = False, label='Bill Value')
    bill_date      = forms.DateField(required = False, label='Bill Date')
    purachase_date = forms.DateField(required = False, label='Purchase Date')
    inst_date      = forms.DateField(required = False, label='Installation Date')
    po_number      = forms.CharField(required = False, label='Purchase Order Number', max_length = 100)
    far_asset_id   = forms.CharField(required = False, label='FAR Asset Id', max_length = 100)
    invoice_date   = forms.DateField(required = False, label='Invoice Date')
    invoice_no     = forms.CharField( required = False, label='Invoice No.', max_length = 100)
    supplier       = forms.CharField(required = False, max_length = 50)
    meter          = forms.ChoiceField(choices=[], required = False, initial='NONE', label='Meter')
    model          = forms.CharField(label='Model', required = False, max_length = 100)

    class Meta:
        model = Asset
        fields = ['assetcode', 'assetname', 'enable', 'runningstatus', 'type', 'parent',
                   'iscritical', 'category', 'subcategory', 'identifier',
                  'capacity', 'unit', 'brand', 'ctzoffset']

        widgets = {
            'assetcode'    : forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'})
        }
    
    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'ASSET'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        #utils.initailize_form_fields(self)
        
    
    def clean_assetname(self):
        if value := self.cleaned_data.get('assetname'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError("[Invalid name] Only these special characters [-, _, @, #] are allowed in name field")
        return value

class SmartPlaceForm(forms.ModelForm):

    error_msg = {
            'invalid_latlng': "Please enter a correct gps coordinates."
        }
    
    class Meta:
        model = Asset
        fields = ['assetcode', 'assetname', 'identifier', 'ctzoffset', 'runningstatus',
                  'type', 'parent', 'iscritical', 'enable']
        labels = {
            'assetcode':'Code', 'assetname':'Name', 'enable':'Enable',
            'type': 'Type', 'iscritical':'Critical', 'runningstatus':"Status",
            'parent':'Belongs To'
        }


    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['identifier'].initial = 'SMARTPLACE'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        self.fields['parent'].queryset = Asset.objects.filter(
            Q(identifier='LOCATION') & Q(enable = True) | Q(assetcode='NONE'))
        self.fields['type'].queryset = om.TypeAssist.objects.filter(tatype__tacode__in = ['ASSETTYPE', 'ASSET_TYPE'])

    
    def clean(self):
        super().clean()
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        return self.cleaned_data

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


class CheckpointForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_assetcode'  : 'Spaces are not allowed in [Code]',
        'invalid_assetcode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_assetcode3' : "[Invalid code] Code should not endwith '.' ",
        'invalid_latlng'  : "Please enter a correct gps coordinates."
    }
    request=None


    class Meta:
        model = Asset
        fields = ['assetcode', 'assetname', 'runningstatus', 'parent',
            'iscritical', 'enable', 'identifier', 'ctzoffset', 'type', 'location']
        labels = {'location':'Location', 'parent':'Belongs To'}
        

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super(CheckpointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'})
        self.fields['runningstatus'] = forms.ChoiceField(
            choices=Asset.RunningStatus.choices,
            required=True,
            label="Running Status",
            widget=s2forms.Select2Widget(
                attrs={
                    'data-theme': 'bootstrap5'
                }
            )
        )
        self.fields['location'].widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'})
        self.fields['type'].widget = s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'})
        self.fields['assetcode'].widget.attrs = {'style':"text-transform:uppercase"}
        if self.instance.id is None:
            self.fields['parent'].initial = 1
        self.fields['identifier'].initial = 'CHECKPOINT'
        self.fields['type'].required = False
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        
        #filters for dropdown fields
        self.fields['location'].queryset = Location.objects.filter(Q(enable = True) | Q(loccode='NONE'), bu_id = S['bu_id'])
        self.fields['parent'].queryset = Asset.objects.filter(Q(enable=True)| Q(assetcode='NONE'), bu_id = S['bu_id'])
        self.fields['type'].queryset = om.TypeAssist.objects.filter(client_id = S['client_id'], tatype__tacode = 'CHECKPOINTTYPE')
        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if " " in self.data.get('assetcode'):
            raise ValidationError(f": The '{self.data.get('assetcode')}' contains spaces, which is not allowed.")
        if self.data.get('assetcode') == self.cleaned_data['parent'].assetcode:
            raise forms.ValidationError(": Code and Belongs To cannot be same!")
        return self.cleaned_data

    
        
    def clean_assetcode(self):
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        import re
        if value := self.cleaned_data.get('assetcode'):
            regex = "^[a-zA-Z0-9\-_()#)]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_assetcode'])
            if  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_assetcode2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_assetcode3'])
            return value.upper()
        
    def clean_gpslocation(self, val):
        import re
        if gps := val:
            if gps == 'NONE': return None
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            gps = gps.replace('(', '').replace(')', '')
            if not re.match(regex, gps):
               raise forms.ValidationError(self.error_msg['invalid_latlng'])
            gps.replace(' ', '')
            lat, lng = gps.split(',')
            gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return gps
    
    def check_nones(self, cd):
        fields = {
            'parent': 'get_or_create_none_asset',
            'servprov'   : 'get_or_create_none_bv',
            'type'       : 'get_none_typeassist',
            'category'   : 'get_none_typeassist',
            'subcategory': 'get_none_typeassist',
            'brand'      : 'get_none_typeassist',
            'unit'       : 'get_none_typeassist',
            'location'   : 'get_or_create_none_location'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
    
class AssetComparisionForm(forms.Form):
    required_css_class = "required"
    
    asset_type = forms.ChoiceField(label="Asset Type", required=True, choices=[], widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    asset = forms.ChoiceField(label="Asset", required=True, choices=[], widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    qset = forms.ChoiceField(label="Question Set", required=True, choices=[], widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    question = forms.ChoiceField(label="Question", required=True, choices=[], widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    fromdate = forms.DateField(label='From', required=True)
    uptodate = forms.DateField(label='To', required=True)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['asset_type'].choices = om.TypeAssist.objects.get_asset_types_choices(self.request)
        utils.initailize_form_fields(self)
        
    
class ParameterComparisionForm(forms.Form):
    required_css_class = "required"
    
    asset_type = forms.ChoiceField(label="Asset Type", required=True, choices=[], widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    asset = forms.ChoiceField(label="Asset", required=True, choices=[], widget=s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}))
    question = forms.ChoiceField(label="Question", required=True, choices=[], widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    fromdate = forms.DateField(label='From', required=True)
    uptodate = forms.DateField(label='To', required=True)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['asset_type'].choices = om.TypeAssist.objects.get_asset_types_choices(self.request)
        utils.initailize_form_fields(self)
    