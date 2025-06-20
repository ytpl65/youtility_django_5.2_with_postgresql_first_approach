from django.contrib import admin
from .models import ScheduleReport

@admin.register(ScheduleReport)
class ScheduleReportAdmin(admin.ModelAdmin):
    fields = ['report_type', 'report_name', 'filename', 'report_sendtime', 'cron']
    list_display = ['report_type', 'cron', 'report_params']
    list_display_links = ['report_type']
    
    def get_queryset(self, request):
        return ScheduleReport.objects.select_related().all()
