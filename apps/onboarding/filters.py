from django.db.models import fields
import django_filters
from .models import TypeAssist, Bt

class TypeAssistFilter(django_filters.FilterSet):
    tacode = django_filters.CharFilter(field_name='tacode', lookup_expr='icontains', label='Code')
    tatype = django_filters.CharFilter(field_name='tatype', lookup_expr='icontains', label='Type')
    taname = django_filters.CharFilter(field_name='taname', lookup_expr='icontains', label='Name')
    cuser = django_filters.CharFilter(field_name='cuser__peoplecode', lookup_expr='icontains', label='Created By')

    class Meta:
        model = TypeAssist
        fields = ['tacode', 'taname', 'tatype',  'cuser']

class BtFilter(django_filters.FilterSet):
    bucode     = django_filters.CharFilter(field_name='bucode', lookup_expr='icontains', label='Code')
    buname     = django_filters.CharFilter(field_name='buname', lookup_expr='icontains', label='Name')
    butype     = django_filters.CharFilter(field_name='butype__tacode', lookup_expr='icontains', label='Site Type')
    identifier = django_filters.CharFilter(field_name='identifier__tacode', lookup_expr='icontains', label='Type')
    parent     = django_filters.CharFilter(field_name='parent__bucode', lookup_expr='icontains', label='Belongs to')
    butree     = django_filters.CharFilter(field_name='butree', lookup_expr='icontains', label="Reporting Structure")
    enable     = django_filters.CharFilter(field_name='enable', lookup_expr='icontains', label="Enable")

    class Meta:
        model = Bt
        fields = ['bucode', 'buname', 'identifier', 'enable', 'parent', 'butype', 'butree']

class ClientFiler(django_filters.FilterSet):
    bucode = django_filters.CharFilter(field_name='bucode', lookup_expr='icontains', label='Code')
    buname = django_filters.CharFilter(field_name='buname', lookup_expr='icontains', label='Name')
    enable = django_filters.CharFilter(field_name='enable', lookup_expr='icontains', label='Enable')
    bu_preferences__webcapability = django_filters.CharFilter(field_name='bu_preferences__webcapability', lookup_expr='icontains', label='Web Capability')
    bu_preferences__mobcapability = django_filters.CharFilter(field_name='bu_preferences__mobcapability', lookup_expr='icontains', label='Mob Capability')
    bu_preferences__reportcapability = django_filters.CharFilter(field_name='bu_preferences__reportcapability', lookup_expr='icontains', label='Report Capability')

    class Meta:
        model = Bt
        fields = ['bucode', 'buname', 'enable', 'bu_preferences__webcapability',
                 'bu_preferences__mobcapability', 'bu_preferences__reportcapability']
