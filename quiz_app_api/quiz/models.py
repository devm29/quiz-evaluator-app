"""Persistence model for the quiz.

Three tables:

* ``Question``  — the catalogue of question text, de-duplicated by text so the
  same wording is never stored twice. ``answer_text`` holds the reference
  answer and is what the ``exact-match`` scoring strategy grades against.
* ``QuizAnswer`` — one candidate's answer to one question.
* ``Quiz``      — one submitted attempt, linking the answers it contains.
"""

from django.db import models


class Question(models.Model):
    """A question in the catalogue, uniquely identified by its text."""

    # CharField rather than TextField: the uniqueness constraint needs a
    # b-tree index, and several backends refuse to index an unbounded TEXT
    # column. max_length on a TextField is a form hint only and is not
    # enforced by the database at all.
    question_text = models.CharField(max_length=500, unique=True)
    answer_text = models.TextField(max_length=800, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.question_text


class QuizAnswer(models.Model):
    """One answer given to one question as part of a submitted quiz."""

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    submitted_answer = models.TextField(max_length=800, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"answer {self.pk} to question {self.question_id}"


class Quiz(models.Model):
    """A single submitted attempt at the quiz."""

    question_response = models.ManyToManyField(
        QuizAnswer, blank=True, related_name="quizzes"
    )
    submitted_by = models.CharField(max_length=150, blank=True, default="")
    evaluated_by = models.CharField(max_length=150, blank=True, default="")
    score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        # Newest first: the admin, the only read path, wants the
        # most recent submissions, and the index on submitted_at keeps that
        # ordering cheap as the table grows.
        ordering = ["-submitted_at", "-id"]
        verbose_name_plural = "quizzes"

    def __str__(self) -> str:
        return f"quiz {self.pk} by {self.submitted_by or 'anonymous'}"
