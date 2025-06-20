from django.conf import settings
from django.urls import path
from django.urls.conf import include
from django.conf.urls.static import static
from apps.peoples import views


app_name = 'peoples'
urlpatterns = [
    path('peole_form/change_paswd/',  views.ChangePeoplePassword.as_view(), name='people_change_paswd'),
    path('capability/',  views.Capability.as_view(),    name='capability'),
    path('peoplegroup/',  views.PeopleGroup.as_view(),    name='peoplegroup'),
    path('sitegroup/',  views.SiteGroup.as_view(),    name='sitegroup'),
    path('people/',  views.PeopleView.as_view(),    name='people'),
    path('verifyemail/', views.verifyemail, name='verify_email'),
    path('no-site/', views.NoSite.as_view(), name='no_site'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
