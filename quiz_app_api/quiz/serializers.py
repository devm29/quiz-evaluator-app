"""Request validation for the submit-quiz endpoint.

All validation lives here so the view stays a thin HTTP adapter and the
service layer can assume it is handed a well-formed
:class:`~quiz.dto.QuizSubmission`.

The wire format is camelCase because that is what the existing React client
and the published API contract use; the mapping to snake_case happens once,
at this boundary.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework import serializers

from quiz.dto import AnswerInput, QuizSubmission

# These strings are part of the published API contract: the browser client
# renders `msg` verbatim, so they are kept stable rather than inherited from
# DRF's generic wording.
MISSING_FIELDS = "Missing required fields"
MISSING_QUESTION_TEXT = "Question text is required"
EMPTY_QUESTION_LIST = "Question list must be a non-empty array"
TOO_MANY_QUESTIONS = "Too many questions in a single submission"
INVALID_SUBMISSION = "Invalid quiz submission"


def unwrap_payload(request_data: Any) -> dict[str, Any] | None:
    """Accept both documented payload shapes.

    The React client posts ``{"data": {...}}``; the API README documents the
    bare ``{...}`` object. Both are supported, so neither client nor docs had
    to be broken to make them agree.
    """
    if not isinstance(request_data, dict):
        return None
    payload = request_data.get("data", request_data)
    if not isinstance(payload, dict):
        return None
    return payload


class AnswerSerializer(serializers.Serializer):
    """One ``{questionText, answerText}`` pair."""

    questionText = serializers.CharField(
        max_length=500,
        trim_whitespace=True,
        error_messages={
            "required": MISSING_QUESTION_TEXT,
            "blank": MISSING_QUESTION_TEXT,
            "null": MISSING_QUESTION_TEXT,
        },
    )
    answerText = serializers.CharField(
        max_length=800,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=False,
    )


class QuizSubmissionSerializer(serializers.Serializer):
    """The full submission body."""

    submittedBy = serializers.CharField(
        max_length=150,
        allow_blank=True,
        error_messages={"required": MISSING_FIELDS, "null": MISSING_FIELDS},
    )
    evaluatedBy = serializers.CharField(
        max_length=150,
        allow_blank=True,
        error_messages={"required": MISSING_FIELDS, "null": MISSING_FIELDS},
    )
    # The published contract sends score as a JSON string ("0") in some
    # clients and as a number in others; IntegerField accepts both and — the
    # point of the change — rejects "abc" with a 400 instead of letting it
    # blow up inside the ORM as a 500.
    score = serializers.IntegerField(
        error_messages={"required": MISSING_FIELDS, "null": MISSING_FIELDS}
    )
    question = serializers.ListField(
        child=AnswerSerializer(),
        allow_empty=False,
        error_messages={
            "required": MISSING_FIELDS,
            "null": MISSING_FIELDS,
            "empty": EMPTY_QUESTION_LIST,
            "not_a_list": EMPTY_QUESTION_LIST,
        },
    )

    def validate_question(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Bound the size of a single submission.

        The cap is read here rather than baked into the field at import time
        so that an operator can retune it without a redeploy of the module
        and so tests can override it.
        """
        cap = settings.QUIZ_MAX_QUESTIONS_PER_SUBMISSION
        if len(value) > cap:
            raise serializers.ValidationError(TOO_MANY_QUESTIONS)
        return value

    def to_submission(self) -> QuizSubmission:
        """Convert validated data into the framework-free domain object."""
        data = self.validated_data
        return QuizSubmission(
            submitted_by=data["submittedBy"],
            evaluated_by=data["evaluatedBy"],
            reported_score=data["score"],
            answers=tuple(
                AnswerInput(
                    question_text=item["questionText"],
                    answer_text=item.get("answerText", ""),
                )
                for item in data["question"]
            ),
        )


def summarise_errors(errors: Any) -> str:
    """Reduce a nested DRF error structure to one human-readable sentence.

    The endpoint returns the full structure under ``errors``; this picks the
    single message to put in ``msg`` for clients that only display one line.
    ``MISSING_FIELDS`` wins over more specific messages so that a body missing
    several fields reports the obvious problem first.
    """
    messages = list(_walk(errors))
    if not messages:
        return INVALID_SUBMISSION
    if MISSING_FIELDS in messages:
        return MISSING_FIELDS
    return messages[0]


def _walk(node: Any):
    """Yield every leaf string in a nested dict/list of DRF ErrorDetails."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list | tuple):
        for value in node:
            yield from _walk(value)
    elif node is not None:
        yield str(node)
