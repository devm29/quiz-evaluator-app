"""Seed the question catalogue and a few sample submissions.

Idempotent: running it twice leaves the catalogue unchanged and, unless
``--reset`` is passed, does not duplicate the sample submissions. The
container entrypoint runs it on every boot for exactly that reason.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.dto import AnswerInput, QuizSubmission
from quiz.fixtures_data import SEED_QUESTIONS, SEED_SUBMISSIONS
from quiz.models import Question, Quiz
from quiz.scoring import get_strategy
from quiz.services import save_submission


class Command(BaseCommand):
    help = "Populate the question catalogue and a few example submissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing submissions before seeding.",
        )
        parser.add_argument(
            "--questions-only",
            action="store_true",
            help="Seed the question catalogue but no sample submissions.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        created = self._seed_questions()
        self.stdout.write(
            self.style.SUCCESS(
                f"Questions: {created} created, "
                f"{len(SEED_QUESTIONS) - created} already present."
            )
        )

        if options["questions_only"]:
            return

        if options["reset"]:
            deleted, _ = Quiz.objects.all().delete()
            self.stdout.write(f"Removed {deleted} existing quiz rows.")
        elif Quiz.objects.exists():
            self.stdout.write("Submissions already present; skipping sample data.")
            return

        for sample in SEED_SUBMISSIONS:
            quiz = save_submission(self._build_submission(sample))
            self.stdout.write(
                f"Seeded quiz {quiz.pk} for {sample['submitted_by']} "
                f"(score {quiz.score})."
            )
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    @staticmethod
    def _seed_questions() -> int:
        existing = set(
            Question.objects.filter(
                question_text__in=[text for text, _ in SEED_QUESTIONS]
            ).values_list("question_text", flat=True)
        )
        new_rows = [
            Question(question_text=text, answer_text=answer)
            for text, answer in SEED_QUESTIONS
            if text not in existing
        ]
        Question.objects.bulk_create(new_rows, ignore_conflicts=True)
        # Keep reference answers current even for rows an earlier submission
        # created without one.
        for text, answer in SEED_QUESTIONS:
            Question.objects.filter(question_text=text, answer_text="").update(
                answer_text=answer
            )
        return len(new_rows)

    @staticmethod
    def _build_submission(sample: dict) -> QuizSubmission:
        answers = tuple(
            AnswerInput(question_text=text, answer_text=given)
            for (text, _), given in zip(SEED_QUESTIONS, sample["answers"], strict=False)
        )
        submission = QuizSubmission(
            submitted_by=sample["submitted_by"],
            evaluated_by=sample["evaluated_by"],
            reported_score=0,
            answers=answers,
        )
        # Sample rows are graded against the reference answers regardless of
        # the configured strategy, so seeded data is never all zeroes.
        reference = dict(SEED_QUESTIONS)
        graded = get_strategy("exact-match").score(submission, reference)
        return QuizSubmission(
            submitted_by=submission.submitted_by,
            evaluated_by=submission.evaluated_by,
            reported_score=graded,
            answers=submission.answers,
        )
