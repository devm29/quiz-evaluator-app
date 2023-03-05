# quiz_app_api

The Django REST Framework service behind the quiz. Full documentation —
architecture, configuration table, design notes — lives in the
[repository README](../README.md); this file is the per-service quick
reference.

## Requirements

Python 3.10 or newer. (The container image pins 3.11.)

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py seed_quiz        # question catalogue + three sample submissions
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
| `POST` | `/submit_quiz/` | Record one completed quiz. |
| `GET` | `/healthz/` | Liveness plus a database round-trip. Not throttled. |
| — | `/admin/` | The read surface. Needs `createsuperuser`. |

### `POST /submit_quiz/`

The body may be the bare object below or the same object wrapped as
`{"data": {…}}` — the React client sends the wrapped form. Field names are
camelCase.

```json
{
  "submittedBy": "Katherine Johnson",
  "evaluatedBy": "auto",
  "score": 4,
  "question": [
    { "questionText": "Is Milkyway the biggest galaxy in Universe?", "answerText": "No" },
    { "questionText": "Cactus is a flower?(Yes/No)", "answerText": "No" }
  ]
}
```

`answerText` is optional and defaults to `""`. `score` accepts a number or a
numeric string; what is stored depends on `QUIZ_SCORING_STRATEGY` — by default
the client's own number is trusted, and `exact-match` grades against the
reference answers in the catalogue instead.

`201 Created`:

```json
{ "msg": "Quiz response saved successfully", "quizId": 4, "score": 4 }
```

`400 Bad Request` carries a one-line `msg` for the browser and the full
field-level detail under `errors`:

```json
{
  "msg": "Missing required fields",
  "errors": { "score": ["Missing required fields"] }
}
```
