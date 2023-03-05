"""Pluggable grading strategies.

The original API trusted whatever ``score`` the client sent, while the
``Question.answer_text`` column that exists to hold the reference answer was
never read. Rather than hard-code one behaviour, grading is a named strategy
looked up from a registry, selected by the ``QUIZ_SCORING_STRATEGY`` setting.

Adding a new way to grade is: write a class with a ``name`` and a ``score``
method, decorate it with :func:`register_strategy`, import it here. No change
to the view, the serializer or the service.

The default is ``exact-match``: the browser client never computes a score,
so trusting it stored 0 for every real attempt. ``client-reported`` remains for
callers that mark their own quizzes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from quiz.dto import QuizSubmission


@runtime_checkable
class ScoringStrategy(Protocol):
    """Turns a submission into an integer score."""

    name: str

    def score(
        self, submission: QuizSubmission, reference_answers: Mapping[str, str]
    ) -> int:
        """Return the score for *submission*.

        ``reference_answers`` maps question text to the stored reference
        answer (possibly empty) for every question in the submission.
        """


_REGISTRY: dict[str, ScoringStrategy] = {}


def register_strategy(
    cls: Callable[[], ScoringStrategy]
) -> Callable[[], ScoringStrategy]:
    """Class decorator that adds a strategy to the registry by its ``name``."""
    instance = cls()
    if not instance.name:
        raise ValueError(f"{cls!r} must declare a non-empty name")
    if instance.name in _REGISTRY:
        raise ValueError(f"scoring strategy {instance.name!r} is already registered")
    _REGISTRY[instance.name] = instance
    return cls


def available_strategies() -> tuple[str, ...]:
    """Names of every registered strategy, sorted."""
    return tuple(sorted(_REGISTRY))


def get_strategy(name: str) -> ScoringStrategy:
    """Look up a strategy by name, raising a helpful error if it is unknown."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise LookupError(
            f"unknown scoring strategy {name!r}; available: "
            f"{', '.join(available_strategies())}"
        ) from None


@register_strategy
class ClientReportedScoring:
    """Trust the score the client sent."""

    name = "client-reported"

    def score(
        self, submission: QuizSubmission, reference_answers: Mapping[str, str]
    ) -> int:
        return submission.reported_score


@register_strategy
class ExactMatchScoring:
    """One point per answer that matches the stored reference answer.

    Comparison is case-insensitive and ignores surrounding whitespace.
    Questions with no reference answer on record score nothing — an
    un-seeded catalogue therefore grades everything as zero rather than
    silently awarding marks.
    """

    name = "exact-match"

    def score(
        self, submission: QuizSubmission, reference_answers: Mapping[str, str]
    ) -> int:
        total = 0
        for answer in submission.answers:
            expected = (reference_answers.get(answer.question_text) or "").strip()
            if not expected:
                continue
            if answer.answer_text.strip().casefold() == expected.casefold():
                total += 1
        return total
