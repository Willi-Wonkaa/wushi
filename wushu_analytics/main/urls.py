from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [

    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics, name='analytics'),
    path('competitions/', views.competitions, name='competitions'),
    path('competitions/<int:competition_id>/analytics/', views.competition_analytics, name='competition_analytics'),
    path('regions/', views.regions, name='regions'),
    path('regions/<str:region_name>/', views.region_detail, name='region_detail'),
    path('athletes/', views.athletes, name='athletes'),
    path('athletes/<int:athlete_id>/', views.athlete_detail, name='athlete_detail'),
    path('run-parser/', views.update_data, name='run_parser'),
    path('full-sync/', views.full_sync, name='full_sync'),
    path('check-categories/', views.check_categories, name='check_categories'),

]

