"""Tests for the seed_quiz management command."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from quiz.fixtures_data import SEED_QUESTIONS, SEED_SUBMISSIONS
from quiz.models import Question, Quiz


class SeedQuizCommandTests(TestCase):
    def seed(self, *args) -> str:
        out = StringIO()
        call_command("seed_quiz", *args, stdout=out)
        return out.getvalue()

    def test_seeds_questions_with_reference_answers(self):
        self.seed()

        self.assertEqual(Question.objects.count(), len(SEED_QUESTIONS))
        self.assertFalse(Question.objects.filter(answer_text="").exists())

    def test_seeds_sample_submissions(self):
        self.seed()

        self.assertEqual(Quiz.objects.count(), len(SEED_SUBMISSIONS))
        self.assertTrue(Quiz.objects.filter(score__gt=0).exists())

    def test_sample_scores_follow_the_reference_answers(self):
        self.seed()

        scores = dict(Quiz.objects.values_list("submitted_by", "score"))
        self.assertEqual(
            scores, {"Ada Lovelace": 5, "Grace Hopper": 3, "Alan Turing": 3}
        )

    def test_is_idempotent(self):
        self.seed()
        output = self.seed()

        self.assertEqual(Question.objects.count(), len(SEED_QUESTIONS))
        self.assertEqual(Quiz.objects.count(), len(SEED_SUBMISSIONS))
        self.assertIn("skipping sample data", output)

    def test_reset_replaces_existing_submissions(self):
        self.seed()
        self.seed("--reset")

        self.assertEqual(Quiz.objects.count(), len(SEED_SUBMISSIONS))

    def test_questions_only_skips_submissions(self):
        self.seed("--questions-only")

        self.assertEqual(Question.objects.count(), len(SEED_QUESTIONS))
        self.assertFalse(Quiz.objects.exists())

    def test_backfills_a_missing_reference_answer(self):
        text, answer = SEED_QUESTIONS[0]
        Question.objects.create(question_text=text)

        self.seed("--questions-only")

        self.assertEqual(Question.objects.get(question_text=text).answer_text, answer)
