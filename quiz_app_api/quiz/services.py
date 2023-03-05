"""Business logic for saving a quiz submission.

Kept out of the view so it can be unit-tested without HTTP, and so the
transaction boundary is owned by the layer that understands the invariant:
a quiz row and all of its answers are written together or not at all.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import connections, router, transaction

from quiz.dto import QuizSubmission
from quiz.models import Question, Quiz, QuizAnswer
from quiz.scoring import ClientReportedScoring, get_strategy

logger = logging.getLogger(__name__)


@transaction.atomic
def save_submission(submission: QuizSubmission) -> Quiz:
    """Persist *submission* and return the created :class:`Quiz`.

    The write is set-based rather than row-by-row. The original implementation
    ran ``get_or_create`` + ``create`` + m2m ``add`` inside a per-question
    loop, i.e. 3N round-trips for an N-question quiz. This issues a fixed
    handful of statements no matter how many questions arrive.
    """
    questions = _resolve_questions(submission.question_texts)

    reference_answers = {
        text: question.answer_text for text, question in questions.items()
    }
    strategy = get_strategy(settings.QUIZ_SCORING_STRATEGY)
    score = strategy.score(submission, reference_answers)

    # When the server did the marking, say so rather than leave it blank.
    evaluated_by = submission.evaluated_by
    if not evaluated_by and strategy.name != ClientReportedScoring.name:
        evaluated_by = strategy.name

    quiz = Quiz.objects.create(
        submitted_by=submission.submitted_by,
        evaluated_by=evaluated_by,
        score=score,
    )

    answer_rows = [
        QuizAnswer(
            question=questions[answer.question_text],
            submitted_answer=answer.answer_text,
        )
        for answer in submission.answers
    ]
    answers = _create_answers(answer_rows)
    quiz.question_response.add(*answers)

    logger.info(
        "quiz.submitted quiz_id=%s answers=%s score=%s strategy=%s",
        quiz.pk,
        len(answers),
        score,
        strategy.name,
    )
    return quiz


def _resolve_questions(texts: tuple[str, ...]) -> dict[str, Question]:
    """Return a ``{question_text: Question}`` map, creating what is missing.

    Two concurrent submissions can both decide the same question is new;
    ``ignore_conflicts`` lets the loser's insert be dropped by the unique
    constraint instead of raising, and the follow-up read picks up whichever
    row actually landed.
    """
    if not texts:
        return {}

    found = {
        q.question_text: q for q in Question.objects.filter(question_text__in=texts)
    }
    missing = [text for text in texts if text not in found]
    if not missing:
        return found

    Question.objects.bulk_create(
        [Question(question_text=text) for text in missing],
        ignore_conflicts=True,
    )
    # ignore_conflicts leaves primary keys unset on the in-memory instances,
    # so read the rows back rather than trusting the objects we just built.
    found.update(
        {q.question_text: q for q in Question.objects.filter(question_text__in=missing)}
    )
    return found


def _create_answers(rows: list[QuizAnswer]) -> list[QuizAnswer]:
    """Insert answer rows, returning instances that have primary keys.

    ``bulk_create`` only populates primary keys on backends that can return
    rows from a bulk insert (PostgreSQL, and SQLite 3.35+). Everywhere else we
    fall back to individual inserts, because the m2m ``add`` below needs real
    primary keys and a silently empty link table would be worse than N
    queries.
    """
    if not rows:
        return []

    connection = connections[router.db_for_write(QuizAnswer)]
    if connection.features.can_return_rows_from_bulk_insert:
        return QuizAnswer.objects.bulk_create(rows)

    logger.debug(
        "bulk insert cannot return primary keys; falling back to per-row create"
    )
    for row in rows:
        row.save()
    return rows
