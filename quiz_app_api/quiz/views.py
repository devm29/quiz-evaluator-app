"""HTTP adapters.

These are deliberately thin: parse, delegate, format. Validation lives in
``quiz.serializers``, persistence and grading in ``quiz.services``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import DatabaseError, connections
from rest_framework import status, views
from rest_framework.response import Response

from quiz.models import Question
from quiz.serializers import (
    INVALID_SUBMISSION,
    MISSING_FIELDS,
    QuizSubmissionSerializer,
    summarise_errors,
    unwrap_payload,
)
from quiz.services import save_submission

logger = logging.getLogger(__name__)


class QuestionListApiView(views.APIView):
    """``GET /questions/`` — the quiz the client asks, without the answers.

    Only questions with a reference answer are served: submissions can add
    rows to the catalogue with arbitrary text, and those must not leak into
    the quiz. The list is capped at the submission limit so a client can
    always post back everything it was given.
    """

    def get(self, request):
        questions = (
            Question.objects.exclude(answer_text="")
            .order_by("id")
            .values_list("id", "question_text")
        )[: settings.QUIZ_MAX_QUESTIONS_PER_SUBMISSION]
        return Response(
            data={
                "questions": [
                    {"id": pk, "questionText": text} for pk, text in questions
                ]
            }
        )


class SubmitQuizApiView(views.APIView):
    """``POST /submit_quiz/`` — record one completed quiz."""

    def post(self, request):
        payload = unwrap_payload(request.data)
        if payload is None:
            return Response(
                data={"msg": MISSING_FIELDS, "errors": {"detail": INVALID_SUBMISSION}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = QuizSubmissionSerializer(data=payload)
        if not serializer.is_valid():
            return Response(
                data={
                    "msg": summarise_errors(serializer.errors),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quiz = save_submission(serializer.to_submission())
        except DatabaseError:
            # Log with a stack trace for the operator; return a generic
            # message so database internals are not leaked to the client.
            logger.exception("quiz.submit_failed")
            return Response(
                data={"msg": "Something went wrong while saving response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            data={
                "msg": "Quiz response saved successfully",
                "quizId": quiz.pk,
                "score": quiz.score,
            },
            status=status.HTTP_201_CREATED,
        )


class HealthCheckApiView(views.APIView):
    """``GET /healthz/`` — liveness plus a real database round-trip.

    Used by the container healthcheck, so it must not be throttled: a
    rate-limited health probe would report the service down under load.
    """

    throttle_classes: list = []

    def get(self, request):
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            logger.exception("healthcheck.database_unavailable")
            return Response(
                data={"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(data={"status": "ok", "database": "ok"})
