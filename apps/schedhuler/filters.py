import django_filters as dfs
from apps.activity.models.job_model import Job,Jobneed
from django.db.models import Q
import django_filters.widgets as wg
import django_select2.forms as s2forms

def assigned_to_qs(queryset, name, value):
        return queryset.filter(Q(aaatop__peoplename__icontains = value) | Q(pgroup__groupname__icontains = value))

###################### JOB FILTER #########################
class JobFilter(dfs.FilterSet):
    class Meta:
        model  = Job
        fields = [
            'jobname',    'jobdesc',      'fromdate',       'uptodate',  'cron',
            'identifier', 'planduration', 'gracetime',       'expirytime', 'parent',
            'asset',    'priority',     'qset',          'pgroup',    'geofence', 
            'parent',     'seqno',         'client',        'bu',       'starttime', 
            'frequency',  'scantype',     'ticketcategory', 'people',   'shift',
            'endtime',    'ctzoffset',    
        ]

class JobneedFilter(dfs.FilterSet):
    class Meta:
        model = Jobneed
        fields = [
            'identifier', 'frequency',    'parent',         'jobdesc',   'asset', 'ticketcategory',
            'qset',     'people',     'pgroup',        'priority',  'scantype',
            'jobstatus',  'plandatetime', 'expirydatetime', 'gracetime', 'starttime', 'cdtz',
            'endtime',    'performedby',   'cuser',     'muser', 
            'bu',              
        ]

class SchdTourFilter(JobFilter):
    jobname      = dfs.CharFilter(field_name='jobname', lookup_expr='icontains', label='Name')
    assignedto   = dfs.CharFilter(method = assigned_to_qs, label='People/Group')
    planduration = dfs.CharFilter(field_name='planduration', lookup_expr='icontains', label='Duration')
    expirytime   = dfs.CharFilter(field_name='expirytime', lookup_expr='icontains', label='Exp Time')
    gracetime    = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    fromdate    = dfs.DateTimeFilter(field_name='fromdate', lookup_expr='icontains', label='From')
    uptodate    = dfs.DateTimeFilter(field_name='uptodate', lookup_expr='icontains', label='To')

    class Meta(JobFilter.Meta):
        exclude = ['endtime', 'cron', 'client', 'ticketcategory', 'parent', 'seqno', 'frequency', 'pgroup', 'starttime', 'bu',
                   'priority', 'ctzoffset', 'geofence', 'identifier', 'people', 'shift', 'jobdesc', 'scantype', 'assignedto']

class SchdExtTourFilter(SchdTourFilter):
    bu = dfs.CharFilter(field_name='bu__buname', lookup_expr='icontains', label= "BV")

    class Meta(SchdTourFilter.Meta):
        fields = ['jobname',  'bu', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'fromdate', 'uptodate']
        exclude = ['asset']

class SchdTaskFilter(SchdTourFilter):
    asset        = dfs.CharFilter(field_name='asset__assetname', lookup_expr='icontains', label= "Asset")
    class Meta(SchdTourFilter.Meta):
        fields = ['jobname',  'asset', 'qset', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'fromdate', 'uptodate']

class InternalTourFilter(dfs.FilterSet):
    JOBSTATUSCHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('AUTOCLOSED', 'Auto Closed'),
        ('COMPLETED', 'Completed'),
        ('INPROGRESS', 'Inprogress'),
        ('PARTIALLYCOMPLETED', 'Partially Completed')
    ]
    plandatetime   = dfs.DateFromToRangeFilter(widget = wg.RangeWidget(attrs={'placeholder': 'YYYY/MM/DD'}))
    jobdesc        = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Description')
    jobstatus      = dfs.ChoiceFilter(field_name='jobstatus', choices = JOBSTATUSCHOICES, label="Stauts", widget = s2forms.Select2Widget)
    assignedto     = dfs.CharFilter( method = assigned_to_qs, label='People/Group')
    gracetime      = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    performedby   = dfs.CharFilter(field_name='performedby', lookup_expr='icontains', label='Performed By')
    expirydatetime = dfs.DateTimeFilter(field_name='expirydatetime', label="Exp. Datetime")

    class Meta:
        model = Jobneed
        fields = [ 'plandatetime', 'jobdesc', 'jobstatus', 'assignedto', 'gracetime', 'performedby', 'expirydatetime']

    def __init__(self, *args, **kwargs):
        super(InternalTourFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'radioselect', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            if visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'

class TaskListJobneedFilter(InternalTourFilter):
    asset   = dfs.CharFilter(field_name='asset__assetname', lookup_expr='icontains', label='Asset/Smartplace')
    qset    = dfs.CharFilter(field_name='qset__qset_name', lookup_expr='icontains', label='QuestionSetz')
    bu      = dfs.CharFilter(field_name= 'bu__buname', lookup_expr='icontains')
    jobdesc = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Description')

class TicketListFilter(JobneedFilter):
    TICKETSTATUS = [
        ("RESOLVED",  "Resolved"),
        ("OPEN",      "Open"),
        ("CANCELLED", "Cancelled"),
        ("ESCALATED", "Escalated"),
        ("NEW",       "New")
    ]
    cdtz            = dfs.DateTimeFilter(field_name='cdtz', lookup_expr='contains')
    ticketno        = dfs.NumberFilter(field_name='ticketno', lookup_expr='contains')
    assignedto      = dfs.CharFilter(method = assigned_to_qs, label='People/Group')
    performedby    = dfs.CharFilter(field_name='performedby__peoplename', lookup_expr='icontains')
    ticketcategory = dfs.CharFilter(field_name='ticketcategory__taname', lookup_expr='icontains')
    jobstatus       = dfs.ChoiceFilter(field_name='jobstatus', choices = TICKETSTATUS, label="Stauts", widget = s2forms.Select2Widget)
    cuser           = dfs.CharFilter(field_name='cuser__peoplename', lookup_expr='icontains')

    class Meta(JobneedFilter.Meta):
        fields = ['cdtz', 'cuser', 'ticketno', 'bu', 'assignedto', 'performedby', 'ticketcategory', 'jobstatus']

    def __init__(self, *args, **kwargs):
        super(TicketListFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'radioselect', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            if visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'
