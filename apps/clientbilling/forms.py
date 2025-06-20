from django import forms
from .models import Discounts, Features, Billing
from django_select2 import forms as s2forms
from apps.core import utils


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = ['client', 'feature', 'newprice', 'currency', 'isactive', 'ctzoffset']
        widgets = {
            'feature': s2forms.Select2Widget,
            'currency':s2forms.Select2Widget
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


class FeaturesForm(forms.ModelForm):
    required_css_class="required"
    defaultprice = forms.IntegerField(label='Default Price (INR)', required=True, initial=0, help_text="Enter Default price in Rupees")
    class Meta:
        model = Features
        fields = (
            'name', 'defaultprice', 'description', 'isactive',
            'ctzoffset'
        )
        labels = {
            'name': 'Feature Name',
            'description': 'Description',
            'isactive': 'Active',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': "Give the feature name"}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder':"What does this feature do?"}),
        }
        
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        

class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discounts
        fields = ['client', 'discount', 'fromdate', 'uptodate', 'ctzoffset']