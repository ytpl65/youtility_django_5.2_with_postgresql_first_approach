from django.urls import path
from apps.clientbilling import views


app_name = 'clientbilling'
urlpatterns = [
    path('features/', views.FeatureView.as_view(), name='features'),
]