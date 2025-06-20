import django_filters
import apps.attendance.models as atdm
from django import forms

class AttendanceFilter(django_filters.FilterSet):
    FR_CHOICES = ((True, 'Yes'), ('False', 'No'))
    EVENTTYPE_CHOICES = [('MARK', 'Mark'), ('SELF', 'Self'),
                         ('SITE', 'Site'), ('CONVEYANCE', 'Conveyance')]

    people = django_filters.CharFilter(field_name='people__peoplename', lookup_expr='icontains',
                                         label='People', widget = forms.TextInput(attrs={'id': 'people'}))
    bu = django_filters.CharFilter(
        field_name='bu__buname', lookup_expr='icontains', label='Site')
    peventtype = django_filters.CharFilter(
        field_name='peventtype', lookup_expr="icontains", label='Type',)
    facerecognition = django_filters.CharFilter(
        field_name="facerecognition", label="Face Recognition", lookup_expr='icontains')
    verifiedby = django_filters.CharFilter(field_name='verifiedby__peoplename', label='Verified By',
                                           lookup_expr='icontains',  widget = forms.TextInput(attrs={'id': "verifiedby"}))
    punch_intime = django_filters.DateTimeFilter(
        field_name='punch_intime', label='In Time', lookup_expr='contains')
    punch_outtime = django_filters.DateTimeFilter(
        field_name='punch_outtime', label='Out Time', lookup_expr='icontains')
    datefor = django_filters.DateFilter(
        field_name='datefor', label='For Date', lookup_expr='icontains')

    class Meta:
        model = atdm.PeopleEventlog
        fields = ['peventtype', 'bu', 'people',  'facerecognition',
                  'verifiedby', 'datefor', 'punch_intime', 'punch_outtime']
