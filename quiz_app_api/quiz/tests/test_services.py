"""Tests for the persistence service, including its query cost."""

from unittest import mock

from django.db import connections, router
from django.test import TestCase, override_settings

from quiz.dto import AnswerInput, QuizSubmission
from quiz.models import Question, Quiz, QuizAnswer
from quiz.services import save_submission


def build_submission(count: int, **overrides) -> QuizSubmission:
    defaults = {
        "submitted_by": "candidate",
        "evaluated_by": "evaluator",
        "reported_score": 0,
        "answers": tuple(
            AnswerInput(f"Question {index}?", f"answer {index}")
            for index in range(count)
        ),
    }
    defaults.update(overrides)
    return QuizSubmission(**defaults)


# Statements one call to save_submission issues, regardless of how many
# questions it carries: two reads to resolve the catalogue, one insert for the
# questions that were missing, one for the quiz, one bulk insert for the
# answers, one for the m2m rows, plus the savepoint pair TestCase opens around
# the service's own atomic block.
QUERIES_PER_SUBMISSION = 8


class SaveSubmissionTests(TestCase):
    def test_creates_quiz_questions_and_answers(self):
        quiz = save_submission(build_submission(3))

        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 3)
        self.assertEqual(QuizAnswer.objects.count(), 3)
        self.assertEqual(quiz.question_response.count(), 3)

    def test_existing_questions_are_reused_not_duplicated(self):
        Question.objects.create(question_text="Question 0?", answer_text="answer 0")

        save_submission(build_submission(2))

        self.assertEqual(Question.objects.count(), 2)
        # The pre-existing reference answer is left alone.
        self.assertEqual(
            Question.objects.get(question_text="Question 0?").answer_text, "answer 0"
        )

    def test_duplicate_question_text_within_one_submission(self):
        submission = build_submission(
            0,
            answers=(
                AnswerInput("Same question?", "first"),
                AnswerInput("Same question?", "second"),
            ),
        )

        quiz = save_submission(submission)

        self.assertEqual(Question.objects.count(), 1)
        self.assertEqual(quiz.question_response.count(), 2)

    def test_query_count_does_not_grow_with_the_number_of_questions(self):
        """The bottleneck this replaced was a 3N-query per-question loop.

        The number itself is incidental; what matters is that it is the same
        for 2 questions and for 40.
        """
        with self.assertNumQueries(QUERIES_PER_SUBMISSION):
            save_submission(build_submission(2))

        Question.objects.all().delete()
        Quiz.objects.all().delete()

        with self.assertNumQueries(QUERIES_PER_SUBMISSION):
            save_submission(build_submission(40))

    @override_settings(QUIZ_SCORING_STRATEGY="client-reported")
    def test_client_reported_strategy_stores_the_submitted_score(self):
        quiz = save_submission(build_submission(2, reported_score=7))

        self.assertEqual(quiz.score, 7)

    @override_settings(QUIZ_SCORING_STRATEGY="exact-match")
    def test_exact_match_strategy_grades_against_the_catalogue(self):
        Question.objects.create(question_text="Capital of Japan?", answer_text="Tokyo")
        Question.objects.create(question_text="Capital of France?", answer_text="Paris")
        submission = build_submission(
            0,
            reported_score=99,
            answers=(
                AnswerInput("Capital of Japan?", " tokyo "),
                AnswerInput("Capital of France?", "Berlin"),
            ),
        )

        quiz = save_submission(submission)

        self.assertEqual(quiz.score, 1)

    @override_settings(QUIZ_SCORING_STRATEGY="nope")
    def test_unknown_strategy_fails_loudly(self):
        with self.assertRaises(LookupError):
            save_submission(build_submission(1))
        self.assertFalse(Quiz.objects.exists())


class BulkInsertFallbackTests(TestCase):
    """Backends that cannot return rows from a bulk insert take a slower path.

    Modern SQLite and PostgreSQL both can, so the fallback would otherwise
    never execute here — but the m2m links it feeds would be silently empty
    if it broke.
    """

    def test_answers_are_still_linked_without_returning_ids(self):
        connection = connections[router.db_for_write(QuizAnswer)]
        with mock.patch.object(
            type(connection.features),
            "can_return_rows_from_bulk_insert",
            False,
        ):
            # Guard against the patch silently not applying: if this is still
            # True the test would pass while exercising the fast path.
            self.assertFalse(connection.features.can_return_rows_from_bulk_insert)
            quiz = save_submission(build_submission(3))

        self.assertEqual(quiz.question_response.count(), 3)
        self.assertEqual(QuizAnswer.objects.count(), 3)
        self.assertTrue(all(answer.pk for answer in quiz.question_response.all()))
