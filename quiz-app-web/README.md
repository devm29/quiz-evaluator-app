# quiz-app-web

The Pocket Trivia client: React 19, built with Vite and tested with Vitest. The
[repository README](../README.md) covers the whole project; this is the
per-service quick reference.

## Requirements

Node 22.12 or newer (`.nvmrc` pins 22).

## Run it locally

The API must be running first (see [`../quiz_app_api`](../quiz_app_api)).

```bash
npm ci
cp .env.example .env        # sets VITE_API_BASEURL
npm run dev                 # http://localhost:8220
```

```bash
npm run test:ci   # single run
npm test          # watch mode
npm run lint      # ESLint, zero warnings allowed
npm run build     # production bundle in dist/
npm run preview   # serve dist/ on 8220
```

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_BASEURL` | Yes | Base URL of the API, with or without a trailing slash. Vite inlines it at build time, so a change needs a rebuild or a restart of `npm run dev`. Unset, the app shows a configuration error instead of calling a wrong host. |

## Layout

```
src/
├── api.js                 # fetchQuestions, submitQuiz, QuizApiError
├── components/
│   ├── Quiz.jsx           # rendering and effects only
│   ├── quizReducer.js     # every state transition, as one pure function
│   └── clock.js           # m:ss formatting for the countdown
├── constants/constants.js # the per-question time limit
├── style/quiz.css         # palette and type tokens on :root
└── test/questions.js      # API-shaped fixture for the tests
```
