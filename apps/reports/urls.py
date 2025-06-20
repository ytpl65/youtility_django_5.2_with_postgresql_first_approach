from django.urls import path
from apps.reports import views

app_name='reports'
urlpatterns = [
    path('sitereport_list/',           views.RetriveSiteReports.as_view(),             name='sitereport_list'),
    path('incidentreport_list/',       views.RetriveIncidentReports.as_view(),         name='incidentreport_list'),
    path('sitereport_template/',       views.ConfigSiteReportTemplate.as_view(),       name='config_sitereport_template'),
    path('incidentreport_template/',   views.ConfigIncidentReportTemplate.as_view(),   name='config_incidentreport_template'),
    path('workpermitreport_template/', views.ConfigWorkPermitReportTemplate.as_view(), name='config_workpermitreport_template'),
    path('incidentreport_temp_list/',  views.IncidentReportTemplate.as_view(),         name='incidentreport_template_list'),
    path('sitereport_temp_form/',      views.SiteReportTemplateForm.as_view(),         name='sitereport_template_form'),
    path('incidentreport_temp_form/',  views.IncidentReportTemplateForm.as_view(),     name='incident_template_form'),
    path('srqsetbelonging/',           views.MasterReportBelonging.as_view(),          name='srqsetbelonging'),
    path('get_reports/',               views.DownloadReports.as_view(),                name='exportreports'),
    path('get_report_status/',         views.return_status_of_report,                name='report_status'),
    path('design/',                    views.DesignReport.as_view(),                   name='design'),
    path('schedule-email-report/',     views.ScheduleEmailReport.as_view(),            name='schedule_email_report'),
    path('generatepdf/',               views.GeneratePdf.as_view(),                    name="generatepdf"),
    path('generatepdf-getdata/',       views.get_data,                                 name='generatepdf-getdata'),
    path('upload-pdf/',                views.upload_pdf,                               name='upload-pdf'),
    path('generateletter/',            views.GenerateLetter.as_view(),                 name="generateletter"),
    path('generateattendance/',        views.GenerateAttendance.as_view(),             name="generateattendance"),
    path('attendance_template/',       views.AttendanceTemplate.as_view(),             name="attendance_template"),
    path('generate_declaration_form/', views.GenerateDecalartionForm.as_view(),        name="generate_declaration_form"),
]
