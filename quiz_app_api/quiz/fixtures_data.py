"""The shipped quiz: the questions the React client asks, with reference answers.

This lives in the repository rather than in a JSON fixture so that the seed
command and the tests share exactly one definition of "the quiz". The client
fetches the questions from ``GET /questions/``; it never sees the answers.
"""

from __future__ import annotations

SEED_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Which planet is known as the Red Planet?", "Mars"),
    ("What is the chemical symbol for gold?", "Au"),
    ("How many sides does a hexagon have?", "6|six"),
    ("What is the largest ocean on Earth?", "Pacific|Pacific Ocean"),
    ("In which city is the Colosseum?", "Rome"),
)

# Sample submissions so a freshly booted stack has something to look at in the
# admin instead of three empty tables.
SEED_SUBMISSIONS: tuple[dict, ...] = (
    {
        "submitted_by": "Ada Lovelace",
        "evaluated_by": "auto",
        "answers": ("Mars", "Au", "6", "Pacific Ocean", "Rome"),
    },
    {
        "submitted_by": "Grace Hopper",
        "evaluated_by": "auto",
        "answers": ("Mars", "Ag", "six", "Atlantic", "Rome"),
    },
    {
        "submitted_by": "Alan Turing",
        "evaluated_by": "auto",
        "answers": ("Jupiter", "Au", "6", "pacific", "Athens"),
    },
)
