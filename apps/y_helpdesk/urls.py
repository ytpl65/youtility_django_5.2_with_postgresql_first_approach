from django.urls import path
from apps.y_helpdesk import views

app_name = "helpdesk"

urlpatterns = [
    path('escalationmatrix/', views.EscalationMatrix.as_view(), name='escalationmatrix'),
    path('ticket/', views.TicketView.as_view(), name='ticket'),
    path('postingorder/', views.PostingOrderView.as_view(), name='postingorder'),
    path('uniform/', views.UniformView.as_view(), name='uniform'),
]
