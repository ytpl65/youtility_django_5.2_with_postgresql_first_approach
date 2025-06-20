from django.urls import path
from apps.schedhuler import views

app_name = 'schedhuler'
urlpatterns = [
    path('schedhule_tour/',                    views.Schd_I_TourFormJob.as_view(),         name='create_tour'),# job
    path('schedhule_task/',                    views.SchdTaskFormJob.as_view(),            name='create_task'),# job
    path('external_schedhule_tour/',           views.Schd_E_TourFormJob.as_view(),         name='create_externaltour'),# job
    path('external_schedhule_tour/saveSites/', views.save_assigned_sites_for_externaltour, name='save_assigned_sites'),# job
    path('schedhule_tour/<str:pk>/',           views.Update_I_TourFormJob.as_view(),       name='update_tour'),# job
    path('external_schedhule_tour/<str:pk>/',  views.Update_E_TourFormJob.as_view(),       name='update_externaltour'),# job
    path('schedhule_task/<str:pk>/',           views.UpdateSchdTaskJob.as_view(),          name='update_task'),# job
    path('schedhule_tours/',                   views.Retrive_I_ToursJob.as_view(),         name='retrieve_tours'),# job
    path('schedhule_tasks/',                   views.RetriveSchdTasksJob.as_view(),        name='retrieve_tasks'),# job
    path('schedhule_externaltours/',           views.Retrive_E_ToursJob.as_view(),         name='retrieve_externaltours'),# job
    path('delete-checkpoint/',                 views.deleteChekpointFromTour,              name='delete_checkpointTour'),# job
    path('internal-tours/',                    views.Retrive_I_ToursJobneed.as_view(),     name='retrieve_internaltours'),# jobneed
    path('tasklist_jobneed/',                  views.RetrieveTasksJobneed.as_view(),       name='retrieve_tasks_jobneed'),# jobneed
    path('internal-tour/<str:pk>/',            views.Get_I_TourJobneed.as_view(),          name='internaltour'),# jobneed
    path('task_jobneed/<str:pk>/',             views.GetTaskFormJobneed.as_view(),         name='update_task_jobneed'),# jobneed
    path('internal-tour/add/',                 views.add_cp_internal_tour,                 name='add_checkpoint'),# jobneed
    path('runJob/',                            views.run_internal_tour_scheduler,          name='runJob'),
    path('getCronDateTime/',                   views.get_cron_datetime,                    name='getCronDateTime'),

    # SINGLE VIEW CRUD
    path('jobneedtours/', views.JobneedTours.as_view(), name='jobneedtours'),
    path('jobneedexternaltours/', views.JobneedExternalTours.as_view(), name='jobneedexternaltours'),
    # path('jobneedtours/editor/', views.TourJobneedEditorView.as_view(), name='jobneedtourseditor'),
    path('jnd/editor/', views.JobneednJNDEditor.as_view(), name='jn_jnd_editor'),
    path('jobneedtasks/', views.JobneedTasks.as_view(), name='jobneedtasks'),
    path('jobschdtasks/', views.SchdTasks.as_view(), name='jobschdtasks'),
    path('schedule-internal-tour', views.InternalTourScheduling.as_view(), name='schd_internal_tour'),
    path('schedule-external-tour', views.ExternalTourScheduling.as_view(), name='schd_external_tour'),
    path('site_tour_tracking/', views.ExternalTourTracking.as_view(), name="site_tour_tracking")

]
