/**
 * All quiz state transitions in one pure function.
 *
 * The auto-advance timer reads the live draft through the reducer at the
 * moment it fires, so the timer effect depends only on which question is
 * showing and is not restarted by every keystroke.
 */

import { QUESTION_TIME_LIMIT_MS } from "../constants/constants";

/**
 * @typedef {"loading" | "unavailable" | "answering" | "submitting" | "submitted" | "failed"} Phase
 */

export function createInitialState() {
  return {
    /** @type {Array<{questionText: string, answerText: string}>} */
    answers: [],
    index: 0,
    draft: "",
    /** @type {Phase} */
    phase: "loading",
    error: "",
    /** Epoch milliseconds at which the whole attempt runs out. */
    deadline: null,
  };
}

function withDraftRecorded(state) {
  return state.answers.map((answer, position) =>
    position === state.index ? { ...answer, answerText: state.draft } : answer
  );
}

export function quizReducer(state, action) {
  switch (action.type) {
    case "loaded": {
      if (state.phase !== "loading") {
        return state;
      }
      if (action.questions.length === 0) {
        return {
          ...state,
          phase: "unavailable",
          error: "There are no questions yet. Seed the API and reload.",
        };
      }
      return {
        ...state,
        answers: action.questions.map(({ questionText }) => ({
          questionText,
          answerText: "",
        })),
        index: 0,
        draft: "",
        phase: "answering",
        error: "",
        deadline: action.now + action.questions.length * QUESTION_TIME_LIMIT_MS,
      };
    }

    case "loadFailed":
      return state.phase === "loading"
        ? { ...state, phase: "unavailable", error: action.message }
        : state;

    case "reload":
      return state.phase === "unavailable" ? createInitialState() : state;

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
  if (state.phase === "answering") {
    return state.index;
  }
  return ["submitting", "submitted", "failed"].includes(state.phase)
    ? state.answers.length
    : 0;
}
