from django.urls import path
from . import views

app_name = 'pspn'

urlpatterns = [
    path('', views.landing, name="home"),
    path('postponement-request/', views.request_postponement, name="create"),
    path('activity/<int:pk>', views.activity, name="activity"),
    path('activity_two/<int:pk>', views.activity_two, name="activity_two"),
    path('hod/', views.hod, name="hod"),
    path('resume/', views.resume, name="resume"),
    path('dash/', views.dash, name="dash"),
]