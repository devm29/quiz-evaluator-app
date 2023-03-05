"""Model-level guarantees the service layer relies on."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from quiz.models import Question, Quiz, QuizAnswer


class QuestionTests(TestCase):
    def test_question_text_is_unique(self):
        Question.objects.create(question_text="Duplicate?")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Question.objects.create(question_text="Duplicate?")

    def test_answer_text_defaults_to_empty_string(self):
        question = Question.objects.create(question_text="Unanswered?")

        self.assertEqual(question.answer_text, "")

    def test_str_is_the_question_text(self):
        self.assertEqual(str(Question(question_text="Why?")), "Why?")


class QuizTests(TestCase):
    def test_submitted_at_is_set_automatically(self):
        quiz = Quiz.objects.create(submitted_by="candidate")

        self.assertIsNotNone(quiz.submitted_at)

    def test_default_ordering_is_newest_first(self):
        first = Quiz.objects.create(submitted_by="first")
        second = Quiz.objects.create(submitted_by="second")

        self.assertEqual(list(Quiz.objects.all()), [second, first])

    def test_str_falls_back_to_anonymous(self):
        quiz = Quiz.objects.create()

        self.assertEqual(str(quiz), f"quiz {quiz.pk} by anonymous")


class QuizAnswerTests(TestCase):
    def test_answers_are_reachable_from_the_question(self):
        question = Question.objects.create(question_text="Q?")
        QuizAnswer.objects.create(question=question, submitted_answer="A")

        self.assertEqual(question.answers.count(), 1)

    def test_deleting_a_question_cascades_to_its_answers(self):
        question = Question.objects.create(question_text="Q?")
        QuizAnswer.objects.create(question=question, submitted_answer="A")

        question.delete()

        self.assertFalse(QuizAnswer.objects.exists())
