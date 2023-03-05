import { useEffect, useReducer } from "react";
import Countdown from "react-countdown";

import { QUESTION_TIME_LIMIT_MS } from "../constants/constants";
import { fetchQuestions, submitQuiz } from "../api";
import { formatClock } from "./clock";
import { answeredCount, createInitialState, quizReducer } from "./quizReducer";

import "../style/quiz.css";

const Quiz = () => {
  const [state, dispatch] = useReducer(quizReducer, undefined, createInitialState);

  const { answers, deadline, draft, error, index, name, phase, score } = state;
  const total = answers.length;
  const isLastQuestion = index + 1 === total;

  useEffect(() => {
    if (phase !== "loading") {
      return undefined;
    }
    let cancelled = false;
    fetchQuestions()
      .then((questions) => {
        if (!cancelled) {
          dispatch({ type: "loaded", questions });
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          dispatch({ type: "loadFailed", message: loadError.message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [phase]);

  // Per-question time limit. Depends on the question showing, not on what is
  // being typed, so the clock is not restarted by every keystroke.
  useEffect(() => {
    if (phase !== "answering") {
      return undefined;
    }
    const timeoutId = setTimeout(
      () => dispatch({ type: "advance" }),
      QUESTION_TIME_LIMIT_MS
    );
    return () => clearTimeout(timeoutId);
  }, [phase, index]);

  // One POST per transition into the submitting phase. The submit button is
  // not rendered outside the answering phase, so a double click cannot
  // produce a second request.
  useEffect(() => {
    if (phase !== "submitting") {
      return undefined;
    }
    let cancelled = false;
    // No score: the API marks the answers against its own catalogue.
    submitQuiz({ question: answers, submittedBy: name.trim() })
      .then((result) => {
        if (!cancelled) {
          dispatch({ type: "submitted", score: result.score });
        }
      })
      .catch((submitError) => {
        if (!cancelled) {
          dispatch({ type: "failed", message: submitError.message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [phase, answers, name]);

  const answered = answeredCount(state);
  const progressPercent = total ? Math.round((answered / total) * 100) : 0;

  return (
    // No aria-live on the whole card: the countdown would be read out every
    // second. The panels that change announce themselves instead.
    <main className="quiz">
      <header className="quiz__header">
        <p className="quiz__eyebrow">General knowledge</p>
        <h1 className="quiz__title">Pocket Trivia</h1>
        {phase === "answering" ? (
          <p className="quiz__timer">
            <span>Time left</span>
            <Countdown
              date={deadline}
              onComplete={() => dispatch({ type: "finish" })}
              renderer={(parts) => <time>{formatClock(parts)}</time>}
            />
          </p>
        ) : null}
      </header>

      <div
        className="quiz__progress"
        role="progressbar"
        aria-valuenow={answered}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label="Questions answered"
      >
        <span
          className="quiz__progress-bar"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {phase === "loading" ? (
        <section className="quiz__panel">
          <p className="quiz__status" role="status">
            Loading the questions…
          </p>
        </section>
      ) : null}

      {phase === "unavailable" ? (
        <section className="quiz__panel quiz__panel--error">
          <h2 className="quiz__done-title">The quiz could not be loaded</h2>
          <p className="quiz__error" role="alert">
            {error}
          </p>
          <button
            type="button"
            className="quiz__button"
            onClick={() => dispatch({ type: "reload" })}
          >
            Try again
          </button>
        </section>
      ) : null}

      {phase === "ready" ? (
        <section className="quiz__panel">
          <h2 className="quiz__question">
            {total} questions, {QUESTION_TIME_LIMIT_MS / 60000} minutes each
          </h2>
          <p className="quiz__hint">
            Type each answer and press Enter. A question moves on by itself when
            its time runs out, and your answers are marked when you submit.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              dispatch({ type: "start", now: Date.now() });
            }}
          >
            <label className="quiz__label" htmlFor="name">
              Your name <span className="quiz__optional">(optional)</span>
            </label>
            <input
              id="name"
              className="quiz__input"
              autoComplete="name"
              maxLength={150}
              value={name}
              onChange={(event) =>
                dispatch({ type: "name", value: event.target.value })
              }
            />
            <button type="submit" className="quiz__button">
              Start the quiz
            </button>
          </form>
        </section>
      ) : null}

      {phase === "submitted" ? (
        <section className="quiz__panel quiz__panel--done" role="status">
          <h2 className="quiz__done-title">
            {name.trim() ? `Thank you, ${name.trim()}.` : "Thank you for taking this quiz."}
          </h2>
          {typeof score === "number" ? (
            <p className="quiz__done-body">
              You scored {score} out of {total}.
              <span className="quiz__score" aria-hidden="true">
                {score}/{total}
              </span>
            </p>
          ) : (
            <p className="quiz__done-body">All {total} answers were recorded.</p>
          )}
        </section>
      ) : null}

      {phase === "submitting" ? (
        <section className="quiz__panel">
          <p className="quiz__status" role="status">
            Submitting your answers…
          </p>
        </section>
      ) : null}

      {phase === "failed" ? (
        <section className="quiz__panel quiz__panel--error">
          <h2 className="quiz__done-title">We could not save your answers</h2>
          <p className="quiz__error" role="alert">
            {error}
          </p>
          <button
            type="button"
            className="quiz__button"
            onClick={() => dispatch({ type: "retry" })}
          >
            Try again
          </button>
        </section>
      ) : null}

      {phase === "answering" ? (
        <section className="quiz__panel">
          <p className="quiz__count">
            Question <strong>{index + 1}</strong> of {total}
          </p>
          <h2 className="quiz__question" aria-live="polite">
            {answers[index].questionText}
          </h2>
          <label className="quiz__label" htmlFor="answer">
            Your answer
          </label>
          {/* Focus follows the quiz: the Start button is gone once it is pressed. */}
          <input
            id="answer"
            className="quiz__input"
            autoFocus
            autoComplete="off"
            placeholder="Type your answer"
            value={draft}
            onChange={(event) =>
              dispatch({ type: "draft", value: event.target.value })
            }
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                dispatch({ type: "advance" });
              }
            }}
          />
          <button
            type="button"
            className="quiz__button"
            onClick={() => dispatch({ type: "advance" })}
          >
            {isLastQuestion ? "Submit" : "Next"}
          </button>
          <p className="quiz__hint">
            Each question has a {QUESTION_TIME_LIMIT_MS / 60000} minute limit and
            advances on its own when the time runs out.
          </p>
        </section>
      ) : null}
    </main>
  );
};

export default Quiz;
