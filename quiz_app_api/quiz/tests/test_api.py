"""HTTP-level tests for the submit-quiz endpoint."""

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz.models import Question, Quiz, QuizAnswer


class SubmitQuizApiTests(APITestCase):
    def setUp(self):
        # DRF's throttle state lives in the cache and leaks between tests.
        cache.clear()
        self.url = reverse("submit_quiz")
        self.valid_payload = {
            "submittedBy": "candidate-1",
            "evaluatedBy": "evaluator-1",
            "score": 3,
            "question": [
                {"questionText": "What is Python?", "answerText": "A language"},
                {"questionText": "What is Django?", "answerText": "A framework"},
            ],
        }

    def test_submit_quiz_accepts_plain_payload(self):
        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["msg"], "Quiz response saved successfully")
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(QuizAnswer.objects.count(), 2)
        self.assertEqual(Question.objects.count(), 2)

    def test_submit_quiz_accepts_data_wrapped_payload(self):
        response = self.client.post(
            self.url, {"data": self.valid_payload}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.count(), 1)

    def test_submit_quiz_rejects_missing_fields(self):
        response = self.client.post(
            self.url, {"submittedBy": "candidate-1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Missing required fields")

    def test_submit_quiz_rejects_question_without_text(self):
        invalid_payload = {
            **self.valid_payload,
            "question": [{"answerText": "no question text"}],
        }
        response = self.client.post(self.url, invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Question text is required")

    def test_response_reports_created_quiz_id_and_score(self):
        response = self.client.post(self.url, self.valid_payload, format="json")

        quiz = Quiz.objects.get()
        self.assertEqual(response.data["quizId"], quiz.pk)
        self.assertEqual(response.data["score"], 3)

    def test_submit_quiz_links_answers_to_the_quiz(self):
        self.client.post(self.url, self.valid_payload, format="json")

        quiz = Quiz.objects.get()
        linked = list(quiz.question_response.all())
        self.assertEqual(len(linked), 2)
        self.assertEqual(
            sorted(answer.submitted_answer for answer in linked),
            ["A framework", "A language"],
        )
        self.assertEqual(
            sorted(answer.question.question_text for answer in linked),
            ["What is Django?", "What is Python?"],
        )

    def test_submit_quiz_rejects_empty_question_list(self):
        response = self.client.post(
            self.url, {**self.valid_payload, "question": []}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"], "Question list must be a non-empty array"
        )
        self.assertFalse(Quiz.objects.exists())

    def test_submit_quiz_rejects_non_list_question_field(self):
        response = self.client.post(
            self.url, {**self.valid_payload, "question": "nope"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Quiz.objects.exists())

    def test_non_numeric_score_is_a_client_error_not_a_server_error(self):
        """Regression: the old view let this reach the ORM and returned 500."""
        response = self.client.post(
            self.url, {**self.valid_payload, "score": "not-a-number"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("score", response.data["errors"])
        self.assertFalse(Quiz.objects.exists())

    def test_numeric_string_score_is_accepted(self):
        """The API README documents score as a JSON string."""
        response = self.client.post(
            self.url, {**self.valid_payload, "score": "4"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.get().score, 4)

    def test_answer_text_is_optional(self):
        response = self.client.post(
            self.url,
            {**self.valid_payload, "question": [{"questionText": "Unanswered?"}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(QuizAnswer.objects.get().submitted_answer, "")

    def test_submit_quiz_rejects_a_json_array_body(self):
        response = self.client.post(self.url, [1, 2, 3], format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["msg"], "Missing required fields")

    def test_nothing_is_persisted_when_validation_fails(self):
        self.client.post(self.url, {"question": []}, format="json")

        self.assertFalse(Quiz.objects.exists())
        self.assertFalse(Question.objects.exists())
        self.assertFalse(QuizAnswer.objects.exists())

    @override_settings(QUIZ_MAX_QUESTIONS_PER_SUBMISSION=3)
    def test_oversized_submission_is_rejected(self):
        payload = {
            **self.valid_payload,
            "question": [
                {"questionText": f"Question {index}?", "answerText": "x"}
                for index in range(4)
            ],
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"], "Too many questions in a single submission"
        )
        self.assertFalse(Quiz.objects.exists())

    def test_repeated_submissions_reuse_the_question_catalogue(self):
        self.client.post(self.url, self.valid_payload, format="json")
        self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(Question.objects.count(), 2)
        self.assertEqual(Quiz.objects.count(), 2)
        self.assertEqual(QuizAnswer.objects.count(), 4)


class HealthCheckApiTests(APITestCase):
    def test_healthz_reports_ok(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok", "database": "ok"})
