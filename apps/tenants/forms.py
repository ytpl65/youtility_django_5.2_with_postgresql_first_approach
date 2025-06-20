from django import forms

class SearchFieldForm(forms.Form):
    search_col = forms.ChoiceField(choices=[], required = False)
    search_val = forms.CharField(max_length = 50, min_length = 3, required = False)
