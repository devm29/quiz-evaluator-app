# quiz_app_api

The Django REST Framework service behind Pocket Trivia. Full documentation —
architecture, configuration table, design notes — lives in the
[repository README](../README.md); this file is the per-service quick
reference.

## Requirements

Python 3.13 (`.python-version`; the container image uses the same).

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py seed_quiz        # five sample questions + three sample attempts
DJANGO_DEBUG=true python manage.py runserver 8221
```

```bash
python manage.py test        # the suite
ruff check .                 # lint
black --check .              # formatting
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/questions/` | The quiz to ask, without the answers. |
| `POST` | `/submit_quiz/` | Record and mark one attempt. |
| `GET` | `/healthz/` | Liveness plus a database round-trip. Not throttled. |
| — | `/admin/` | Questions and submissions. Needs `createsuperuser`. |

### `GET /questions/`

Catalogue questions that have a reference answer, in id order, capped at
`QUIZ_MAX_QUESTIONS_PER_SUBMISSION`:

```json
{ "questions": [ { "id": 1, "questionText": "Which planet is known as the Red Planet?" } ] }
```

### `POST /submit_quiz/`

The body may be the bare object below or the same object wrapped as
`{"data": {…}}`; the React client sends the wrapped form. Field names are
camelCase and only `question` is required.

```json
{
  "submittedBy": "Sam Rivera",
  "question": [
    { "questionText": "Which planet is known as the Red Planet?", "answerText": "Mars" },
    { "questionText": "What is the chemical symbol for gold?", "answerText": "Ag" }
  ]
}
```

`answerText` defaults to `""`. With the default `exact-match` strategy the API
marks the answers against the reference answers and records `exact-match` as
the evaluator; `evaluatedBy` and `score` are only used by `client-reported`.

`201 Created`:

```json
{ "msg": "Quiz response saved successfully", "quizId": 4, "score": 1 }
```

`400 Bad Request` carries a one-line `msg` for the browser and the full
field-level detail under `errors`:

```json
{
  "msg": "Question list must be a non-empty array",
  "errors": { "question": ["Question list must be a non-empty array"] }
}
```
