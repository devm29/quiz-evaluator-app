"""HTTP-level tests for the quiz endpoints."""

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

    @override_settings(QUIZ_SCORING_STRATEGY="client-reported")
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

    @override_settings(QUIZ_SCORING_STRATEGY="client-reported")
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


class ServerMarkingTests(APITestCase):
    """What the browser actually sends: no score, no evaluator."""

    def setUp(self):
        cache.clear()
        Question.objects.create(question_text="Capital of Japan?", answer_text="Tokyo")
        Question.objects.create(question_text="Two plus two?", answer_text="4")
        self.url = reverse("submit_quiz")

    def post(self, **extra):
        body = {
            "submittedBy": "Sam",
            "question": [
                {"questionText": "Capital of Japan?", "answerText": "tokyo"},
                {"questionText": "Two plus two?", "answerText": "5"},
            ],
            **extra,
        }
        return self.client.post(self.url, {"data": body}, format="json")

    def test_browser_submission_is_marked_by_the_server(self):
        """Regression: the default strategy stored the browser's literal 0."""
        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["score"], 1)
        quiz = Quiz.objects.get()
        self.assertEqual(quiz.score, 1)
        self.assertEqual(quiz.submitted_by, "Sam")

    def test_server_marking_is_recorded_as_the_evaluator(self):
        self.post()

        self.assertEqual(Quiz.objects.get().evaluated_by, "exact-match")

    def test_an_explicit_evaluator_is_kept(self):
        self.post(evaluatedBy="Ms Rivera")

        self.assertEqual(Quiz.objects.get().evaluated_by, "Ms Rivera")

    def test_a_client_score_cannot_inflate_the_mark(self):
        response = self.post(score=99)

        self.assertEqual(response.data["score"], 1)

    def test_names_and_score_are_optional(self):
        response = self.client.post(
            self.url,
            {"question": [{"questionText": "Two plus two?", "answerText": "4"}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz = Quiz.objects.get()
        self.assertEqual((quiz.submitted_by, quiz.score), ("", 1))

    @override_settings(QUIZ_SCORING_STRATEGY="client-reported")
    def test_client_reported_marking_leaves_the_evaluator_alone(self):
        self.post(score=2)

        quiz = Quiz.objects.get()
        self.assertEqual((quiz.score, quiz.evaluated_by), (2, ""))


class QuestionListApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("questions")

    def test_serves_catalogue_questions_in_order_without_answers(self):
        first = Question.objects.create(question_text="First?", answer_text="a")
        second = Question.objects.create(question_text="Second?", answer_text="b")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "questions": [
                    {"id": first.pk, "questionText": "First?"},
                    {"id": second.pk, "questionText": "Second?"},
                ]
            },
        )
        self.assertNotIn('"a"', response.content.decode())

    def test_questions_added_by_submissions_are_not_served(self):
        Question.objects.create(question_text="Real?", answer_text="yes")
        self.client.post(
            reverse("submit_quiz"),
            {"question": [{"questionText": "Injected?", "answerText": "x"}]},
            format="json",
        )

        served = self.client.get(self.url).json()["questions"]
        texts = [question["questionText"] for question in served]

        self.assertEqual(texts, ["Real?"])

    def test_an_unseeded_catalogue_serves_an_empty_quiz(self):
        response = self.client.get(self.url)

        self.assertEqual(response.json(), {"questions": []})

    @override_settings(QUIZ_MAX_QUESTIONS_PER_SUBMISSION=2)
    def test_never_serves_more_than_one_submission_can_carry(self):
        for index in range(3):
            Question.objects.create(question_text=f"Q{index}?", answer_text="x")

        self.assertEqual(len(self.client.get(self.url).json()["questions"]), 2)

    def test_post_is_not_allowed(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class HealthCheckApiTests(APITestCase):
    def test_healthz_reports_ok(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok", "database": "ok"})
