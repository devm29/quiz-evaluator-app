"""Tests for the scoring strategy registry."""

from django.test import SimpleTestCase

from quiz.dto import AnswerInput, QuizSubmission
from quiz.scoring import (
    ClientReportedScoring,
    ExactMatchScoring,
    ScoringStrategy,
    accepted_answers,
    available_strategies,
    get_strategy,
    register_strategy,
)


def submission(*pairs, reported_score=0) -> QuizSubmission:
    return QuizSubmission(
        submitted_by="candidate",
        evaluated_by="",
        reported_score=reported_score,
        answers=tuple(AnswerInput(question, answer) for question, answer in pairs),
    )


class RegistryTests(SimpleTestCase):
    def test_built_in_strategies_are_registered(self):
        self.assertEqual(available_strategies(), ("client-reported", "exact-match"))

    def test_get_strategy_returns_the_named_instance(self):
        self.assertIsInstance(get_strategy("exact-match"), ExactMatchScoring)

    def test_unknown_name_raises_with_the_available_options(self):
        with self.assertRaises(LookupError) as ctx:
            get_strategy("bogus")

        self.assertIn("client-reported", str(ctx.exception))

    def test_duplicate_registration_is_rejected(self):
        with self.assertRaises(ValueError):

            @register_strategy
            class Duplicate:
                name = "exact-match"

                def score(self, submission, reference_answers):
                    return 0

    def test_nameless_strategy_is_rejected(self):
        with self.assertRaises(ValueError):

            @register_strategy
            class Nameless:
                name = ""

                def score(self, submission, reference_answers):
                    return 0

    def test_built_ins_satisfy_the_protocol(self):
        self.assertIsInstance(ClientReportedScoring(), ScoringStrategy)
        self.assertIsInstance(ExactMatchScoring(), ScoringStrategy)


class ClientReportedScoringTests(SimpleTestCase):
    def test_returns_the_reported_score_verbatim(self):
        strategy = ClientReportedScoring()

        self.assertEqual(strategy.score(submission(reported_score=5), {}), 5)


class ExactMatchScoringTests(SimpleTestCase):
    def setUp(self):
        self.strategy = ExactMatchScoring()
        self.reference = {"Q1": "Yes", "Q2": "No", "Q3": ""}

    def test_one_point_per_matching_answer(self):
        score = self.strategy.score(
            submission(("Q1", "Yes"), ("Q2", "No")), self.reference
        )

        self.assertEqual(score, 2)

    def test_matching_ignores_case_and_surrounding_whitespace(self):
        score = self.strategy.score(submission(("Q1", "  yES ")), self.reference)

        self.assertEqual(score, 1)

    def test_wrong_answers_score_nothing(self):
        score = self.strategy.score(submission(("Q1", "No")), self.reference)

        self.assertEqual(score, 0)

    def test_questions_without_a_reference_answer_score_nothing(self):
        score = self.strategy.score(
            submission(("Q3", "anything"), ("Unknown", "anything")), self.reference
        )

        self.assertEqual(score, 0)

    def test_the_reported_score_is_ignored(self):
        score = self.strategy.score(
            submission(("Q1", "No"), reported_score=99), self.reference
        )

        self.assertEqual(score, 0)

    def test_any_listed_alternative_scores(self):
        strategy = ExactMatchScoring()
        reference = {"Sides on a hexagon?": "6|six", "Largest ocean?": "Pacific"}

        result = strategy.score(
            submission(("Sides on a hexagon?", " Six "), ("Largest ocean?", "pacific")),
            reference,
        )

        self.assertEqual(result, 2)

    def test_an_empty_answer_never_matches_a_stray_separator(self):
        strategy = ExactMatchScoring()

        result = strategy.score(submission(("Q?", "")), {"Q?": "yes||"})

        self.assertEqual(result, 0)


class AcceptedAnswersTests(SimpleTestCase):
    def test_splits_strips_and_casefolds(self):
        self.assertEqual(
            accepted_answers(" Pacific | Pacific Ocean "),
            frozenset({"pacific", "pacific ocean"}),
        )

    def test_blank_reference_accepts_nothing(self):
        self.assertEqual(accepted_answers(""), frozenset())
        self.assertEqual(accepted_answers(None), frozenset())
