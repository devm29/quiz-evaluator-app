/**
 * All quiz state transitions in one pure function.
 *
 * Keeping them here rather than in a pile of `useState` calls fixes two
 * classes of bug the component used to have:
 *
 * 1. The rendered question came from the imported constant while the answers
 *    were accumulated in component state, so there were two sources of truth
 *    for the same list.
 * 2. The auto-advance timer closed over the answer being typed, so it either
 *    captured a stale value or had to be reset on every keystroke. A reducer
 *    reads the live draft at the moment it fires, so the timer depends only on
 *    which question is showing.
 */

import questions from "../constants/constants";

/** @typedef {"answering" | "submitting" | "submitted" | "failed"} Phase */

export function createInitialState() {
  return {
    /** @type {Array<{questionText: string, answerText: string}>} */
    answers: questions.map((question) => ({ ...question })),
    index: 0,
    draft: "",
    /** @type {Phase} */
    phase: "answering",
    error: "",
  };
}

function withDraftRecorded(state) {
  return state.answers.map((answer, position) =>
    position === state.index ? { ...answer, answerText: state.draft } : answer
  );
}

export function quizReducer(state, action) {
  switch (action.type) {
    case "draft":
      return state.phase === "answering"
        ? { ...state, draft: action.value }
        : state;

    case "advance": {
      if (state.phase !== "answering") {
        return state;
      }
      const answers = withDraftRecorded(state);
      const nextIndex = state.index + 1;
      if (nextIndex < answers.length) {
        return { ...state, answers, index: nextIndex, draft: "" };
      }
      return { ...state, answers, phase: "submitting", error: "" };
    }

    // The overall countdown expired: keep whatever has been answered so far
    // and submit immediately, from whichever question is on screen.
    case "finish":
      if (state.phase !== "answering") {
        return state;
      }
      return {
        ...state,
        answers: withDraftRecorded(state),
        phase: "submitting",
        error: "",
      };

    case "retry":
      return state.phase === "failed"
        ? { ...state, phase: "submitting", error: "" }
        : state;

    case "submitted":
      return { ...state, phase: "submitted" };

    case "failed":
      return { ...state, phase: "failed", error: action.message };

    default:
      return state;
  }
}

/** Number of questions that have been moved past, for the progress bar. */
export function answeredCount(state) {
  return state.phase === "answering" ? state.index : state.answers.length;
}
