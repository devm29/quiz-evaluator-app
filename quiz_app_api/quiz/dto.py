"""Plain data structures that carry a submission between layers.

These deliberately contain no Django imports: the serializer produces them,
the scoring strategies read them, and the service turns them into rows. That
keeps validation, grading and persistence independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnswerInput:
    """One answer as submitted by the client."""

    question_text: str
    answer_text: str


@dataclass(frozen=True, slots=True)
class QuizSubmission:
    """A complete, validated quiz submission."""

    submitted_by: str
    evaluated_by: str
    reported_score: int
    answers: tuple[AnswerInput, ...]

    @property
    def question_texts(self) -> tuple[str, ...]:
        """Unique question texts, in the order they were first submitted."""
        seen: dict[str, None] = {}
        for answer in self.answers:
            seen.setdefault(answer.question_text, None)
        return tuple(seen)
