from django.urls import path
from . import views

app_name = "learning"

urlpatterns = [
    path("start/", views.study, name="start"),
    path("results/", views.results, name="results"),

    path(
        "quiz/start/<int:topic_id>/",
        views.start_quiz,
        name="start_quiz"
    ),
    path(
        "quiz/<int:attempt_id>/",
        views.quiz_detail,
        name="quiz_detail"
    ),
]