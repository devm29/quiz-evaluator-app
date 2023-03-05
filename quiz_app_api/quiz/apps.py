from django.apps import AppConfig


class QuizConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"

    def ready(self) -> None:
        # Fail at boot rather than on the first submission if the configured
        # scoring strategy does not exist. This matches how the environment
        # helpers behave: a typo is rejected, never silently defaulted.
        from django.conf import settings

        from quiz.scoring import get_strategy

        get_strategy(settings.QUIZ_SCORING_STRATEGY)
