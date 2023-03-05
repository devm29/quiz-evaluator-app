"""Tests for payload unwrapping, validation and error summarising."""

from django.test import SimpleTestCase, override_settings

from quiz.serializers import (
    EMPTY_QUESTION_LIST,
    INVALID_SUBMISSION,
    MISSING_FIELDS,
    MISSING_QUESTION_TEXT,
    TOO_MANY_QUESTIONS,
    QuizSubmissionSerializer,
    summarise_errors,
    unwrap_payload,
)

VALID = {
    "submittedBy": "candidate",
    "evaluatedBy": "",
    "score": "0",
    "question": [{"questionText": "Q1", "answerText": "A1"}],
}


class UnwrapPayloadTests(SimpleTestCase):
    def test_bare_object_is_returned_unchanged(self):
        self.assertEqual(unwrap_payload({"a": 1}), {"a": 1})

    def test_data_wrapper_is_unwrapped(self):
        self.assertEqual(unwrap_payload({"data": {"a": 1}}), {"a": 1})

    def test_non_dict_body_returns_none(self):
        self.assertIsNone(unwrap_payload([1, 2]))
        self.assertIsNone(unwrap_payload("nope"))

    def test_non_dict_data_value_returns_none(self):
        self.assertIsNone(unwrap_payload({"data": [1, 2]}))


class QuizSubmissionSerializerTests(SimpleTestCase):
    def test_valid_payload_converts_to_a_domain_object(self):
        serializer = QuizSubmissionSerializer(data=VALID)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        submission = serializer.to_submission()

        self.assertEqual(submission.submitted_by, "candidate")
        self.assertEqual(submission.reported_score, 0)
        self.assertEqual(len(submission.answers), 1)
        self.assertEqual(submission.answers[0].question_text, "Q1")

    def test_question_texts_are_deduplicated_in_submission_order(self):
        serializer = QuizSubmissionSerializer(
            data={
                **VALID,
                "question": [
                    {"questionText": "B", "answerText": ""},
                    {"questionText": "A", "answerText": ""},
                    {"questionText": "B", "answerText": ""},
                ],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertEqual(serializer.to_submission().question_texts, ("B", "A"))

    def test_blank_question_text_is_rejected(self):
        serializer = QuizSubmissionSerializer(
            data={**VALID, "question": [{"questionText": "   "}]}
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(summarise_errors(serializer.errors), MISSING_QUESTION_TEXT)

    def test_over_length_question_text_is_rejected(self):
        serializer = QuizSubmissionSerializer(
            data={**VALID, "question": [{"questionText": "x" * 501}]}
        )

        self.assertFalse(serializer.is_valid())

    @override_settings(QUIZ_MAX_QUESTIONS_PER_SUBMISSION=2)
    def test_submission_size_cap_is_enforced(self):
        serializer = QuizSubmissionSerializer(
            data={
                **VALID,
                "question": [{"questionText": f"Q{i}"} for i in range(3)],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(summarise_errors(serializer.errors), TOO_MANY_QUESTIONS)

    @override_settings(QUIZ_MAX_QUESTIONS_PER_SUBMISSION=2)
    def test_submission_at_the_cap_is_accepted(self):
        serializer = QuizSubmissionSerializer(
            data={
                **VALID,
                "question": [{"questionText": f"Q{i}"} for i in range(2)],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class SummariseErrorsTests(SimpleTestCase):
    def test_missing_fields_wins_over_more_specific_messages(self):
        serializer = QuizSubmissionSerializer(data={"question": []})
        serializer.is_valid()

        self.assertEqual(summarise_errors(serializer.errors), MISSING_FIELDS)

    def test_empty_question_list_message(self):
        serializer = QuizSubmissionSerializer(data={**VALID, "question": []})
        serializer.is_valid()

        self.assertEqual(summarise_errors(serializer.errors), EMPTY_QUESTION_LIST)

    def test_empty_error_structure_falls_back_to_a_generic_message(self):
        self.assertEqual(summarise_errors({}), INVALID_SUBMISSION)
        self.assertEqual(summarise_errors(None), INVALID_SUBMISSION)

    def test_nested_structures_are_flattened(self):
        self.assertEqual(
            summarise_errors({"question": [{"questionText": ["deep message"]}]}),
            "deep message",
        )
