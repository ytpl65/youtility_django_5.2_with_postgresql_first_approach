import django_filters
from apps.activity.models.question_model import Question,QuestionSet

class QuestionFilter(django_filters.FilterSet):
    quesname   = django_filters.CharFilter(field_name='quesname', lookup_expr='icontains', label='Name')
    answertype = django_filters.CharFilter(field_name='answertype', lookup_expr='icontains', label='Type')
    unit       = django_filters.CharFilter(field_name='unit__tacode', lookup_expr='icontains', label='Unit')
    isworkflow = django_filters.CharFilter(field_name='isworkflow', lookup_expr='icontains', label='Is WorkFlow')

    class Meta:
        model = Question
        fields = ['quesname', 'answertype', 'unit', 'isworkflow']


class MasterQsetFilter(django_filters.FilterSet):
    qsetname   = django_filters.CharFilter(field_name='qsetname', lookup_expr='icontains', label='Name')

    class Meta:
        model = QuestionSet
        fields = ['qsetname']

class MasterAssetFilter(django_filters.FilterSet):
    assetcode   = django_filters.CharFilter(field_name='assetcode', lookup_expr='icontains', label='Code')
    assetname = django_filters.CharFilter(field_name='assetname', lookup_expr='icontains', label='Name')
    parent       = django_filters.CharFilter(field_name='parent__assetcode', lookup_expr='icontains', label='Belongs To')
    runningstatus = django_filters.CharFilter(field_name='runningstatus', lookup_expr='icontains', label='Status')
    enable = django_filters.CharFilter(field_name='enable', lookup_expr='icontains', label='Enable')
    gpslocation = django_filters.CharFilter(field_name='gpslocation', lookup_expr='icontains', label='GPS Location')

    class Meta:
        model = Question
        fields = ['assetcode', 'assetname', 'parent', 'runningstatus', 'enable', 'gpslocation']
