from attr import fields
import django_filters as dfs
from apps.activity.models.job_model import Jobneed
from apps.activity.models.question_model import QuestionSet
import django_filters.widgets as wg
from django_select2 import forms as s2forms


class SiteReportListFilter(dfs.FilterSet):
    JOBSTATUSCHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('AUTOCLOSED', 'Auto Closed'),
        ('COMPLETED', 'Completed'),
        ('INPROGRESS', 'Inprogress'),
        ('PARTIALLYCOMPLETED', 'Partially Completed')
    ]

    plandatetime = dfs.DateFromToRangeFilter(widget = wg.RangeWidget(attrs={'placeholder': 'YYYY/MM/DD'}), label='Plan Datetime')
    jobdesc      = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Site Report')
    jobstatus    = dfs.ChoiceFilter(field_name='jobstatus', choices = JOBSTATUSCHOICES, label="Status", widget = s2forms.Select2Widget)
    peopleid     = dfs.CharFilter(field_name='peopleid__peoplename', lookup_expr='icontains', label='Surveyor')
    bu           = dfs.CharFilter(field_name='bu__buname', lookup_expr='icontains', label='Site')
    gpslocation  = dfs.CharFilter(field_name='gpslocation', lookup_expr='icontains', label='GPS Location')
    distance     = dfs.CharFilter(field_name='distance', lookup_expr='icontains', label='Distance')
    remarks      = dfs.CharFilter(field_name='remarks', lookup_expr='icontains', label='Remarks')

    class Meta:
        model = Jobneed
        fields = ('plandatetime', 'jobdesc', 'peopleid', 'bu', 'jobstatus', 'gpslocation',
                  'distance', 'remarks')

    def __init__(self, *args, **kwargs):
        super(SiteReportListFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'radioselect', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            if visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'

class MasterReportTemplateFilter(dfs.FilterSet):
    qsetname = dfs.CharFilter(field_name='qsetname', lookup_expr='qset_name__icontains', label='Site Report')
    enable = None
    class Meta:
        model = QuestionSet
        fields = ('qsetname', 'enable')
