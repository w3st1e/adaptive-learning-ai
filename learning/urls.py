from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("start/", views.study, name="start"),
    path("results/", views.results, name="results"),
]
