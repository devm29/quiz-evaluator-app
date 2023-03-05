"""The shipped quiz: the questions the React client asks, with reference answers.

This lives in the repository rather than in a JSON fixture so that the seed
command and the tests share exactly one definition of "the quiz".

Note the duplication with ``quiz-app-web/src/constants/constants.js``: the API
has no endpoint that serves questions, so the client carries its own copy.
That is called out in the README's limitations.
"""

from __future__ import annotations

SEED_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Is Milkyway the biggest galaxy in Universe?", "No"),
    ("Cactus is a flower?(Yes/No)", "No"),
    ("Is Tokyo the capital of Japan?(Yes/No)", "Yes"),
    ("Is China the most populated country in the world?(Yes/No)", "No"),
    ("Algae is a plant?(Yes/No)", "No"),
)

# Sample submissions so a freshly booted stack has something to look at in the
# admin instead of three empty tables.
SEED_SUBMISSIONS: tuple[dict, ...] = (
    {
        "submitted_by": "Ada Lovelace",
        "evaluated_by": "auto",
        "answers": ("No", "No", "Yes", "No", "No"),
    },
    {
        "submitted_by": "Grace Hopper",
        "evaluated_by": "auto",
        "answers": ("Yes", "No", "Yes", "Yes", "No"),
    },
    {
        "submitted_by": "Alan Turing",
        "evaluated_by": "auto",
        "answers": ("No", "Yes", "Yes", "No", "Maybe"),
    },
)
