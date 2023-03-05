# quiz-app-web

The Create React App client. Full documentation — architecture, screenshots,
design notes — lives in the [repository README](../README.md); this file is the
per-service quick reference.

## Requirements

Node 18 or newer.

## Run it locally

The API must be running first (see [`../quiz_app_api`](../quiz_app_api)).

```bash
npm install
cp .env.example .env        # sets REACT_APP_API_BASEURL
PORT=8220 npm start
```

The app is then on <http://localhost:8220>.

```bash
npm run test:ci   # single run, no watcher
npm run lint      # eslint, zero warnings tolerated
npm run build     # production bundle
```

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `REACT_APP_API_BASEURL` | **Yes** | none | Base URL of the API, with or without a trailing slash. Create React App inlines it at **build** time, so a change needs a rebuild or a restart of `npm start`, not a page refresh. Unset, the app fails loudly rather than posting to a wrong host. |

## Layout

```
src/
├── components/
│   ├── quiz.js          # rendering and effects only
│   └── quizReducer.js   # every state transition, as one pure function
├── constants/           # the five questions and the time limits
└── routes/
    ├── api.js           # QuizPost + QuizApiError
    └── routes.js
```
