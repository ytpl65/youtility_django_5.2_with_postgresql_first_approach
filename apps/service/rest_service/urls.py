from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.service.rest_service import views

router = DefaultRouter()
router.register(r'people', viewset=views.PeopleViewset, basename='people')
router.register(r'peopleevents', viewset=views.PELViewset, basename='peopleevents')
router.register(r'bt', viewset=views.BtViewset, basename='bt')
router.register(r'shift', viewset=views.ShiftViewset, basename='shifts')
router.register(r'typeassist', viewset=views.TypeAssistViewset, basename='typeassists')
router.register(r'pgroup', viewset=views.PgroupViewset, basename='pgroups')
router.register(r'pgbelonging', viewset=views.PgbelongingViewset, basename='pgbelongings')
router.register(r'job', viewset=views.JobViewset, basename='jobs')
router.register(r'jobneed', viewset=views.JobneedViewset, basename='jobneeds')

urlpatterns = router.urls
