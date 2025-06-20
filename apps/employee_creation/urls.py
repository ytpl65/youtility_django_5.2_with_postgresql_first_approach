from django.urls import path
from . import views
app_name = 'employee_creation'
urlpatterns = [
    path('employee/create/', views.employee_create, name='employee_creation'),
    path('employee/list/', views.employee_list, name='employee_list'),
]