from django.contrib import admin
from .models import Tenant
from import_export.admin import ImportExportModelAdmin
from import_export import resources

# Register your models here.
class TenantResource(resources.ModelResource):
    class Meta:
        model = Tenant
        skip_unchanged = True
        report_skipped = True
        fields = ['tenantname', 'subdomain_prefix']

@admin.register(Tenant)
class TenantAdmin(ImportExportModelAdmin):
    resource_class = TenantResource
    fields = ('tenantname', 'subdomain_prefix')
    list_display = ('tenantname', 'subdomain_prefix', 'created_at')
    list_display_links =  ('tenantname', 'subdomain_prefix', 'created_at')
