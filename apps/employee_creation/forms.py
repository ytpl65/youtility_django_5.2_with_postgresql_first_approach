from django import forms
from .models import Employee, Reference, Experience

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        labels = {
            'full_name': 'Full Name (as per Aadhaar)',  # Manually set the label here
            'post_applied_for': 'Post Applied for',
            'first_name': 'First Name',
            'middle_name': 'Middle Name',
            'marital_status': 'Marital Status',
            'birth_place': 'Birth Place',
            'local_address': 'Local Address',
            'civilian_or_ex_serviceman': 'Civilian/Ex-serviceman',
            'identification_mark': 'Identification Mark',
            'conviction_details': 'Conviction Details',
            'educational_qualification': 'Educational Qualification',
            'police_verification': 'Police Verification',
            'aadhar_no': 'Aadhar No',
            'pan_card_no': 'Pan Card No',
            'ration_card' : 'Ration Card',
            'gun_license_no': 'Gun License No',
            'gun_uin_no': 'Gun Uin No',
            'gun_registration': 'Gun Registration',
            'gun_issue_place': 'Gun Issue Place',
            'gun_issue_authority': 'Gun Issue Authority',
            'gun_license_expiry': 'Gun License Expiry',
            'experience_details': 'Experience Details',
            'emergency_contact_name': 'Emergency Contact Name',
            'emergency_contact_relationship': 'Emergency Contact Relationship',
            'emergency_contact_phone': 'Emergency Contact Phone',
            'emergency_contact_pin': 'Emergency Contact Pincode',
            'emergency_contact_address': 'Emergency Contact Address', 
            'emergency_contact_directions': 'Emergency Contact Directions',
            'mother_name': 'Mother Name',
            'father_name': 'Father Name',
            'children_details': 'Children Details',
            'spouse_name': 'Spouse Name',
            'relatives_details': 'Relatives Details',
            'post_office': 'Post Office',
            'police_station': 'Police Station',
            'hometown_pin_code': 'Hometown Pincode',
            'hometown_phone': 'Hometown Phone No',
            'hometown_directions': 'Hometown Directions',
            'has_experience': 'Has Prior Experience?'
        }
        exclude = ['created_at', 'updated_at', 'approval_status', 'remarks']
        
class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        exclude = ('employee',)
        labels = {
            'time_known': 'Time Known'
        }

ReferenceFormSet = forms.inlineformset_factory(
    Employee,
    Reference,
    form=ReferenceForm,
    extra=0,
    min_num=2,
    validate_min=True,
)

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        exclude = ('employee',)
        labels = {
            'company_name': 'Company Name',
            'designation': 'Designation',
            'salary': 'Salary (INR)',
            'address': 'Address',
            'years_of_experience': 'Years of Experience',
        }
        # Make all fields required
        widgets = {
            'company_name': forms.TextInput(attrs={'required': True}),
            'designation': forms.TextInput(attrs={'required': True}),
            'salary': forms.NumberInput(attrs={'required': True}),
            'address': forms.Textarea(attrs={'required': True}),
            'years_of_experience': forms.NumberInput(attrs={'required': True}),
        }

ExperienceFormSet = forms.inlineformset_factory(
    Employee,
    Experience,
    form=ExperienceForm,
    extra=1,
    can_delete=True,
)