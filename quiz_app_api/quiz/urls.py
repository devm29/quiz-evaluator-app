from django.urls import path

from quiz.views import HealthCheckApiView, SubmitQuizApiView

urlpatterns = [
    path("submit_quiz/", SubmitQuizApiView.as_view(), name="submit_quiz"),
    path("healthz/", HealthCheckApiView.as_view(), name="healthz"),
]
