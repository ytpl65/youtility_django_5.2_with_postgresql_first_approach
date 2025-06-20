from django.urls import path
from apps.activity.views.question_views import Question, QuestionSet, QsetNQsetBelonging, Checkpoint, deleteQSB
from apps.activity.views.asset_views import AssetView, AssetMaintainceList, AssetComparisionView, ParameterComparisionView,PeopleNearAsset,AssetLogView
from apps.activity.views.location_views import LocationView
from apps.activity.views.job_views import PPMView, PPMJobneedView, AdhocTasks, AdhocTours, CalendarView
from apps.activity.views.attachment_views import Attachments, PreviewImage
from apps.activity.views.deviceevent_log_views import MobileUserLog, MobileUserDetails
app_name = 'activity'
urlpatterns = [
    path('question/', Question.as_view(), name='question'),
    path('questionset/', QuestionSet.as_view(), name='checklist'),
    #path('questionset/', views.QuestionSet.as_view(), name='questionset'),
    path('checkpoint/', Checkpoint.as_view(), name='checkpoint'),
    #path('smartplace/', views.Smartplace.as_view(), name='smartplace'),
    path('ppm/', PPMView.as_view(), name='ppm'),
    path('ppm_jobneed/', PPMJobneedView.as_view(), name='ppmjobneed'),
    path('asset/', AssetView.as_view(), name='asset'),
    path('location/', LocationView.as_view(), name='location'),
    path('delete_qsb/', deleteQSB, name='delete_qsb'),
    #path('esclist/', views.RetriveEscList.as_view(), name='esc_list'),
    path('adhoctasks/', AdhocTasks.as_view(), name='adhoctasks'),
    path('adhoctours/', AdhocTours.as_view(), name='adhoctours'),
    path('assetmaintainance/', AssetMaintainceList.as_view(), name='assetmaintainance'),
    path('qsetnQsetblng/', QsetNQsetBelonging.as_view(), name='qset_qsetblng'),
    path('mobileuserlogs/', MobileUserLog.as_view(), name='mobileuserlogs'),
    path('mobileuserdetails/', MobileUserDetails.as_view(), name='mobileuserdetails'),
    path('peoplenearassets/', PeopleNearAsset.as_view(), name='peoplenearasset'),
    path('attachments/', Attachments.as_view(), name='attachments'),
    path('previewImage/', PreviewImage.as_view(), name='previewImage'),
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('assetlog/', AssetLogView.as_view(), name="assetlogs"),
    path('comparision/', AssetComparisionView.as_view(), name="comparision"),
    path('param_comparision/', ParameterComparisionView.as_view(), name="param_comparision")
]
