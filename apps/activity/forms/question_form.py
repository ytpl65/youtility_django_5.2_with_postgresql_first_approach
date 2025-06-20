import re
import django_select2.forms as s2forms
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.activity.models.question_model import Question, QuestionSet,QuestionSetBelonging
from apps.activity.models.asset_model import Asset
from apps.activity.models.location_model import Location

import apps.activity.utils as ac_utils
import apps.onboarding.models as om
import apps.peoples.models as pm
from apps.core import utils

class QuestionForm(forms.ModelForm):
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    required_css_class = "required"
    alertbelow         = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')
    options = forms.CharField(max_length=2000, required=False, label='Options', widget=forms.TextInput(attrs={'placeholder': 'Enter options separated by comma (,)'}))

    class Meta:
        model = Question
        fields = ['quesname', 'answertype', 'alerton', 'isworkflow', 'isavpt', 'avpttype',
                  'unit', 'category', 'options', 'isworkflow', 'min', 'max', 'ctzoffset']
        labels = {
            'quesname' : 'Name',
            'answertype': 'Type',
            'unit'      : 'Unit',
            'category'  : 'Category',
            'min'       : 'Min Value',
            'max'       : 'Max Value',
            'alerton'   : 'Alert On',
            'isworkflow': 'used in workflow?',
        }

        widgets = {
            'answertype': s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'category'  : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'unit'      : s2forms.Select2Widget(attrs={'data-theme':'bootstrap5'}),
            'alerton'   : s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}),
        }

    def __init__(self, *args, **kwargs):  # sourcery skip: use-named-expression
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['min'].initial       = None
        self.fields['max'].initial       = None
        self.fields['category'].required = False
        self.fields['unit'].required     = False
        self.fields['alerton'].required  = False
        
        #filters for dropdown fields
        self.fields['unit'].queryset = om.TypeAssist.objects.select_related('tatype').filter(tatype__tacode = 'QUESTIONUNIT', client_id = S['client_id'])
        self.fields['category'].queryset = om.TypeAssist.objects.select_related('tatype').filter(tatype__tacode = 'QUESTIONCATEGORY', client_id = S['client_id'])
        
        if self.instance.id:
            ac_utils.initialize_alertbelow_alertabove(self.instance, self)
        utils.initailize_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data
        alertabove = alertbelow = None
        if(data.get('answertype') not in ['NUMERIC', 'RATING', 'CHECKBOX', 'DROPDOWN']):
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
            cleaned_data['alerton'] = cleaned_data['options'] = None
        if data.get('answertype') in  ['CHECKBOX', 'DROPDOWN', 'MULTISELECT']:
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
        if data.get('answertype') in ['NUMERIC', 'RATING']:
            cleaned_data['options'] = None
        if data.get('alertbelow') and data.get('min') not in [None, ""]:
            alertbelow = ac_utils.validate_alertbelow(forms, data)
        if data.get('alertabove') and data.get('max') not in [None, '']:
            alertabove = ac_utils.validate_alertabove(forms, data)
        if data.get('answertype') == 'NUMERIC' and alertabove and alertbelow:
            alerton = f'<{alertbelow}, >{alertabove}'
            cleaned_data['alerton'] = alerton

    def clean_alerton(self):
        if val := self.cleaned_data.get('alerton'):
            return ac_utils.validate_alerton(forms, val)
        else:
            return val

    def clean_options(self):
        if val := self.cleaned_data.get('options'):
            return ac_utils.validate_options(forms, val)
        else:
            return val
    
    def clean_min(self):
        return val if (val := self.cleaned_data.get('min')) else 0.0
    
    def clean_max(self):
        val = val if (val := self.cleaned_data.get('max')) else 0.0
        return val
    
            

class MasterQsetForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    assetincludes = forms.MultipleChoiceField(
        required = True, label='Checkpoint', widget = s2forms.Select2MultipleWidget)
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label="Site Types", required=False)
    buincludes         = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site Includes', required=False)
    site_grp_includes  = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site groups', required=False)

    class Meta:
        model = QuestionSet
        fields = ['qsetname', 'parent', 'enable', 'assetincludes', 'type', 'ctzoffset', 'site_type_includes', 'buincludes', 'site_grp_includes']

        labels = {
            'parent': 'Parent',
            'qsetname': 'Name', }
        widgets = {
            'parent': s2forms.Select2Widget()
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        super().__init__(*args, **kwargs)
        self.fields['type'].initial      = 'ASSET'
        self.fields['type'].widget.attrs = {"style": "display:none;"}
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tatype__tacode = "SITETYPE") | Q(tacode='NONE'), client_id = self.request.session['client_id']).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_bu_of_client(self.request.session['client_id'])
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist)).values_list('id', 'groupname')
        utils.initailize_form_fields(self)
    
    def clean_qsetname(self):
        if value := self.cleaned_data.get('qsetname'):
            regex = r"^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError("[Invalid name] Only these special characters [-, _, @, #] are allowed in name field")
        return value

class QsetBelongingForm(forms.ModelForm):
    required_css_class = "required"
    alertbelow = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')
    options = forms.CharField(max_length=2000, required=False, label='Options', widget=forms.TextInput(attrs= {'placeholder':'Enter options separated by comma ","'}))


    class Meta:
        model = QuestionSetBelonging
        fields = ['seqno', 'qset', 'question', 'answertype', 'min', 'max',
                  'isavpt', 'avpttype',
                  'alerton', 'options', 'ismandatory', 'ctzoffset']
        widgets = {
            'answertype': forms.TextInput(attrs={'readonly': 'readonly'}),
            'question'    : s2forms.Select2Widget,
            'alerton'   : s2forms.Select2MultipleWidget,
            'options'   : forms.Textarea(attrs={'rows': 3, 'cols': 40}),
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        super().__init__(*args, **kwargs)
        self.fields['min'].initial = None
        self.fields['max'].initial = None
        for k in self.fields.keys():
            if k in ['min', 'max']:
                self.fields[k].required = True
            elif k in ['options', 'alerton']:
                self.fields[k].required = False
        if self.instance.id:
            ac_utils.initialize_alertbelow_alertabove(self.instance, self)
        utils.initailize_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data
        alertabove = alertbelow = None
        if(data.get('answertype') not in ['NUMERIC', 'RATING', 'CHECKBOX', 'DROPDOWN']):
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
            cleaned_data['alerton'] = cleaned_data['options'] = None
        if data.get('answertype') in  ['CHECKBOX', 'DROPDOWN']:
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
        if data.get('answertype') in ['NUMERIC', 'RATING']:
            cleaned_data['options'] = None
        if data.get('alertbelow') and data.get('min'):
            alertbelow = ac_utils.validate_alertbelow(forms, data)
        if data.get('alertabove') and data.get('max'):
            alertabove = ac_utils.validate_alertabove(forms, data)
        if data.get('answertype') == 'NUMERIC' and alertabove and alertbelow:
            alerton = f'<{alertbelow}, >{alertabove}'
            cleaned_data['alerton'] = alerton

    def clean_alerton(self):
        val = self.cleaned_data.get('alerton')
        if val:
            return ac_utils.validate_alerton(forms, val)
        return val

    def clean_options(self):
        val = self.cleaned_data.get('options')
        if val:
            return ac_utils.validate_options(forms, val)
        return val

    def validate_unique(self) -> None:
        super().validate_unique()
        if not self.instance.id:
            try:
                Question.objects.get(
                    quesname__exact   = self.instance.quesname,
                    answertype__iexact = self.instance.answertype,
                    client_id__exact = self.request.session['client_id'])
                msg = 'This type of Question is already exist!'
                raise forms.ValidationError(
                    message = msg, code="unique_constraint")
            except Question.DoesNotExist:
                pass
            except ValidationError as e:
                self._update_errors(e)

class ChecklistForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    assetincludes = forms.MultipleChoiceField(
        required = True, label='Checkpoint', widget = s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}))
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}), label="Site Types", required=False)
    buincludes         = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}), label='Site Includes', required=False)
    site_grp_includes  = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget(attrs={'data-theme':'bootstrap5'}), label='Site groups', required=False)
    
    class Meta:
        model = QuestionSet
        fields = ['qsetname', 'enable', 'type', 'ctzoffset', 'assetincludes', 'show_to_all_sites',
                  'site_type_includes', 'buincludes', 'site_grp_includes', 'parent']
        widgets = {
            'parent':forms.TextInput(attrs={'style':'display:none'}),
        }


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['type'].initial        = 'CHECKLIST'
        self.fields['parent'].required = False
        #self.fields['type'].widget.attrs   = {"style": "display:none;"}
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1
            self.fields['assetincludes'].initial = 1
        else: 
            self.fields['type'].required = False
        
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tacode='NONE') |  Q(client_id = S['client_id']) & Q(tatype__tacode = "SITETYPE"),  enable=True).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_bu_of_client(self.request.session['client_id'])
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist) & Q(client_id = S['client_id'])).values_list('id', 'groupname')
        self.fields['assetincludes'].choices = ac_utils.get_assetsmartplace_choices(self.request, ['CHECKPOINT', 'ASSET'])
        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        if self.instance.id:
            self.cleaned_data['type'] = self.instance.type
        
    def check_nones(self, cd):
        fields = {
            'parent':'get_or_create_none_qset'
            }
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd  


class QuestionSetForm(MasterQsetForm):

    class Meta(MasterQsetForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S  = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['type'].initial          = 'QUESTIONSET'    
        self.fields['assetincludes'].label   = 'Asset/Smartplace'
        self.fields['assetincludes'].choices = ac_utils.get_assetsmartplace_choices(self.request, ['ASSET', 'SMARTPLACE'])
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(tatype__tacode='SITETYPE', client_id = S['client_id']).values_list('id', 'tacode')
        self.fields['type'].widget.attrs     = {"style": "display:none;"}
        if not self.instance.id:
            self.fields['parent'].initial = 1
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1
        utils.initailize_form_fields(self)


