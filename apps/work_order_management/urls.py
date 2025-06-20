from django.urls import path
from apps.work_order_management import views
app_name = 'work_order_management'
urlpatterns = [
    path('vendor/', views.VendorView.as_view(), name="vendor"),
    path('approver/', views.ApproverView.as_view(), name="approvers"),
    path('work_order/',views.WorkOrderView.as_view(), name='workorder' ),
    path('replyworkorder/', views.ReplyWorkOrder.as_view(), name='reply_workorder'),
    path('replyworkpermit/', views.ReplyWorkPermit.as_view(), name='reply_workpermit'),
    path('verifierreplyworkpermit/',views.VerifierReplyWorkPermit.as_view(),name='verifier_reply_workpermit'),
    path('workpermit/', views.WorkPermit.as_view(), name='work_permit'),
    path('sla/',views.SLA_View.as_view(), name='sla'),
    path('replysla/', views.ReplySla.as_view(), name='reply_sla'),
]
