from django.urls import path

from quiz.views import HealthCheckApiView, QuestionListApiView, SubmitQuizApiView

urlpatterns = [
    path("questions/", QuestionListApiView.as_view(), name="questions"),
    path("submit_quiz/", SubmitQuizApiView.as_view(), name="submit_quiz"),
    path("healthz/", HealthCheckApiView.as_view(), name="healthz"),
]
