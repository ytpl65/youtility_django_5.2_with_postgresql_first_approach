from django.db.models import fields
import django_filters
from .models import Capability, People, Pgroup

class PeopleFilter(django_filters.FilterSet):
    peoplecode = django_filters.CharFilter(
        field_name='peoplecode', lookup_expr='icontains', label='Code')
    peoplename = django_filters.CharFilter(
        field_name='peoplename', lookup_expr='icontains', label='Name')
    peopletype = django_filters.CharFilter(
        field_name='peopletype__tacode', lookup_expr='icontains', label='People Type')
    bu = django_filters.CharFilter(
        field_name='bu__bucode', lookup_expr='icontains', label='Is Admin')
    isadmin = django_filters.CharFilter(
        field_name='isadmin', lookup_expr='icontains', label='Code')

    class Meta:
        model = People
        fields = ['peoplecode', 'peoplename', 'peopletype', 'bu', 'isadmin']

class PgroupFilter(django_filters.FilterSet):
    groupname = django_filters.CharFilter(
        field_name='groupname', lookup_expr='icontains', label='Group Name')
    enable = django_filters.CharFilter(
        field_name='enable', lookup_expr='icontains', label='Enable')

    class Meta:
        model = Pgroup
        fields = ['groupname', 'enable']

class CapabilityFilter(django_filters.FilterSet):
    capscode = django_filters.CharFilter(
        field_name='capscode', lookup_expr='icontains', label='Code')
    capsname = django_filters.CharFilter(
        field_name='capsname', lookup_expr='icontains', label='Name')
    cfor = django_filters.CharFilter(
        field_name='cfor', lookup_expr='icontains', label='Capability for')
    parent = django_filters.CharFilter(
        field_name='parent__capscode', lookup_expr='icontains', label='Belongs to')

    class Meta:
        model = Capability
        fields = ['capscode', 'capsname', 'cfor', 'parent']
