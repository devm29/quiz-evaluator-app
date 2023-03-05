import React, { useEffect, useMemo, useReducer } from "react";
import Countdown from "react-countdown";

import { QUESTION_TIME_LIMIT_MS, QUIZ_TIME_LIMIT_MS } from "../constants/constants";
import { QuizPost } from "../routes/api";
import { answeredCount, createInitialState, quizReducer } from "./quizReducer";

import "../style/quiz.css";

const Quiz = () => {
  const [state, dispatch] = useReducer(quizReducer, undefined, createInitialState);
  const deadline = useMemo(() => Date.now() + QUIZ_TIME_LIMIT_MS, []);

  const { answers, draft, error, index, phase } = state;
  const total = answers.length;
  const isLastQuestion = index + 1 === total;

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
    QuizPost({ question: answers, submittedBy: "" })
      .then(() => {
        if (!cancelled) {
          dispatch({ type: "submitted" });
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
  }, [phase, answers]);

  const answered = answeredCount(state);
  const progressPercent = Math.round((answered / total) * 100);

  return (
    <main className="quiz" aria-live="polite">
      <header className="quiz__header">
        <p className="quiz__eyebrow">General knowledge</p>
        <h1 className="quiz__title">Quiz</h1>
        {phase === "answering" ? (
          <p className="quiz__timer">
            Time remaining{" "}
            <Countdown date={deadline} onComplete={() => dispatch({ type: "finish" })} />
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

      {phase === "submitted" ? (
        <section className="quiz__panel quiz__panel--done">
          <h2 className="quiz__done-title">Thank you for taking this quiz.</h2>
          <p className="quiz__done-body">
            All {total} answers were recorded.
          </p>
        </section>
      ) : null}

      {phase === "submitting" ? (
        <section className="quiz__panel">
          <p className="quiz__status">Submitting your answers…</p>
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
          <h2 className="quiz__question">{answers[index].questionText}</h2>
          <label className="quiz__label" htmlFor="answer">
            Your answer
          </label>
          <input
            id="answer"
            className="quiz__input"
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
