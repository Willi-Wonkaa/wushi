from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [

    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics, name='analytics'),
    path('competitions/', views.competitions, name='competitions'),
    path('regions/', views.regions, name='regions'),
    path('athletes/', views.athletes, name='athletes'),
    path('run-parser/', views.run_parser, name='run_parser'),

]

