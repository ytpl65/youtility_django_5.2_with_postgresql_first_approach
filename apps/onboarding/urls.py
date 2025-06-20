from django.urls import path, include
from apps.onboarding import views


app_name = 'onboarding'
urlpatterns = [
    path('client_form/get_caps/',    views.get_caps,name="get_caps"),
    path('pop-up/ta/', views.handle_pop_forms, name="ta_popup"),
    path('typeassist/', views.TypeAssistView.as_view(), name="typeassist"),
    path('super_typeassist/', views.SuperTypeAssist.as_view(), name="super_typeassist"),
    path('shift/', views.ShiftView.as_view(), name="shift"),
    path('editor/', views.EditorTa.as_view(), name="editortypeassist"),
    path('geofence/', views.GeoFence.as_view(), name='geofence'),
    path('import/', views.BulkImportData.as_view(), name="import"),
    path('client/', views.Client.as_view(), name="client"),
    path('bu/', views.BtView.as_view(), name="bu"),
    path('rp_dashboard/', views.DashboardView.as_view(), name="rp_dashboard"),
    path('fileUpload/', views.FileUpload.as_view(), name="file_upload"),
    path('subscription/', views.LicenseSubscriptionView.as_view(), name="subscription"),
    path('import_update/', views.BulkImportUpdate.as_view(), name="import_update"),
    path('contract/', views.ContractView.as_view(), name="contract"),
    path('get_assignedsites/', views.GetAssignedSites.as_view(), name='get_assignedsites'),
    path('get_allsites/', views.GetAllSites.as_view(), name='get_allsites'),
    path('switchsite/',views.SwitchSite.as_view(), name='switchsite'),
    path('list_of_peoples/', views.get_list_of_peoples, name="list_of_peoples"),

]
