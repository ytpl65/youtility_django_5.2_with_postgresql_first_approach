from django import forms
from django.db.models import Q
from .models import Ticket, EscalationMatrix
from apps.onboarding.models import TypeAssist
from apps.core import utils
from apps.peoples.models import Pgroup, People
from apps.activity.models.location_model import Location
from apps.activity.models.asset_model import Asset

class TicketForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = Ticket
        fields = [
            'ticketdesc', 'assignedtopeople', 'assignedtogroup', 'priority', 'ctzoffset',
            'ticketcategory', 'status', 'comments', 'location', 'cdtz',
            'isescalated', 'ticketsource', 'asset'
        ]
        labels = {
            'assignedtopeople':'User', 'assignedtogroup':"User Group", 'ticketdesc':"Subject",
            'cdtz':"Created On", 'ticketcategory':"Queue",
            "isescalated":"Escalated", 'asset':'Asset/Checkpoint'
        }
        widgets={
            'comments' : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'isescalated':forms.TextInput(attrs={'readonly':True}),
            'ticketsource':forms.TextInput(attrs={'style':"display:none"}),
            'ticketdesc':forms.Textarea(attrs={'rows':3})
        }
        

    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['assignedtogroup'].required=False
        self.fields['ticketdesc'].required=True
        self.fields['ticketcategory'].required=True
        self.fields['priority'].required=True
        self.fields['comments'].required=False
        self.fields['ticketsource'].initial=Ticket.TicketSource.USERDEFINED
        
        #filters for dropdown fields
        self.fields['assignedtogroup'].queryset = Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['assignedtopeople'].queryset = People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['ticketcategory'].queryset = TypeAssist.objects.filter(tatype__tacode='TICKETCATEGORY', client_id = S['client_id'], enable=True, bu_id = S['bu_id'])
        self.fields['location'].queryset = Location.objects.filter_for_dd_location_field(self.request, sitewise=True)
        self.fields['asset'].queryset = Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET', 'CHECKPOINT'], sitewise=True)
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['status'].initial = 'NEW'
            #self.fields['assignedtogroup'] = utils.get_or_create_none_pgroup()
    
    def clean(self):
        super().clean()
        cd = self.cleaned_data
        if cd['assignedtopeople'] is None and cd['assignedtogroup'] is None:
            raise forms.ValidationError("Make Sure You Assigned Ticket Either People OR Group")
        self.cleaned_data = self.check_nones(self.cleaned_data)
        
    def clean_ticketdesc(self):
        if val:= self.cleaned_data.get('ticketdesc'):
            val = val.strip()
            val.capitalize()
        return val
    
    def clean_comments(self):
        return val.strip() if (val:= self.cleaned_data.get('comments')) else val
    
    def check_nones(self, cd):
        fields = {
            'location':'get_or_create_none_location',
            'assignedtopeople': 'get_or_create_none_people',
            'assignedtogroup': 'get_or_create_none_pgroup',}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
    


# create a ModelForm
class EscalationForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = EscalationMatrix
        fields = ['escalationtemplate', 'ctzoffset']
        labels = {
            'escalationtemplate':"Escalation Template"
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['escalationtemplate'].queryset = TypeAssist.objects.select_related('tatype').filter(
            Q(bu_id__in = self.request.session['assignedsites'] + [1] ) | Q(cuser_id=1) | Q(cuser__is_superuser=True),
            tatype__tacode__in = ['TICKETCATEGORY', 'TICKET_CATEGORY'],
            
        )