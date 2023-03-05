import {
  answeredCount,
  createInitialState,
  quizReducer,
} from "./quizReducer";
import { QUESTION_TIME_LIMIT_MS } from "../constants/constants";
import { QUESTIONS as questions } from "../test/questions";

const NOW = 1_700_000_000_000;
const draft = (state, value) => quizReducer(state, { type: "draft", value });
const advance = (state) => quizReducer(state, { type: "advance" });
const loaded = () =>
  quizReducer(createInitialState(), { type: "loaded", questions, now: NOW });

describe("quizReducer", () => {
  it("starts out loading with nothing to answer", () => {
    const state = createInitialState();

    expect(state.phase).toBe("loading");
    expect(state.answers).toEqual([]);
    expect(answeredCount(state)).toBe(0);
  });

  it("starts on the first question once the questions arrive", () => {
    const state = loaded();

    expect(state.index).toBe(0);
    expect(state.phase).toBe("answering");
    expect(state.answers).toEqual(
      questions.map(({ questionText }) => ({ questionText, answerText: "" }))
    );
  });

  it("gives the whole attempt one time limit per question", () => {
    expect(loaded().deadline).toBe(NOW + questions.length * QUESTION_TIME_LIMIT_MS);
  });

  it("treats an empty question list as unavailable", () => {
    const state = quizReducer(createInitialState(), {
      type: "loaded",
      questions: [],
      now: NOW,
    });

    expect(state.phase).toBe("unavailable");
    expect(state.error).toMatch(/no questions/);
  });

  it("records a failed load and starts over on reload", () => {
    const failed = quizReducer(createInitialState(), {
      type: "loadFailed",
      message: "offline",
    });
    expect(failed).toMatchObject({ phase: "unavailable", error: "offline" });

    expect(quizReducer(failed, { type: "reload" })).toEqual(createInitialState());
  });

  it("ignores a late load result once the quiz has started", () => {
    const state = loaded();

    expect(quizReducer(state, { type: "loadFailed", message: "x" })).toBe(state);
    expect(quizReducer(state, { type: "loaded", questions: [], now: NOW })).toBe(
      state
    );
    expect(quizReducer(state, { type: "reload" })).toBe(state);
  });

  it("does not keep a reference to the fetched question objects", () => {
    const state = advance(draft(loaded(), "mutated"));

    expect(state.answers[0].answerText).toBe("mutated");
    expect(questions[0]).not.toHaveProperty("answerText");
  });

  it("records the draft against the current question and clears it", () => {
    const state = advance(draft(loaded(), "my answer"));

    expect(state.answers[0].answerText).toBe("my answer");
    expect(state.index).toBe(1);
    expect(state.draft).toBe("");
  });

  it("moves to submitting after the last question", () => {
    let state = loaded();
    for (let i = 0; i < questions.length; i += 1) {
      state = advance(draft(state, `a${i}`));
    }

    expect(state.phase).toBe("submitting");
    expect(state.answers.map((a) => a.answerText)).toEqual(
      questions.map((_, i) => `a${i}`)
    );
  });

  it("advancing while submitting is a no-op", () => {
    let state = loaded();
    for (let i = 0; i < questions.length; i += 1) {
      state = advance(draft(state, "x"));
    }

    expect(advance(state)).toBe(state);
    expect(draft(state, "late")).toBe(state);
  });

  it("finish submits partial answers from the current question", () => {
    let state = advance(draft(loaded(), "first"));
    state = draft(state, "second, unsent");
    state = quizReducer(state, { type: "finish" });

    expect(state.phase).toBe("submitting");
    expect(state.answers[0].answerText).toBe("first");
    expect(state.answers[1].answerText).toBe("second, unsent");
    expect(state.answers[2].answerText).toBe("");
  });

  it("finish after submission is a no-op", () => {
    const submitted = quizReducer(loaded(), { type: "submitted" });

    expect(quizReducer(submitted, { type: "finish" })).toBe(submitted);
  });

  it("failure records the message and retry clears it", () => {
    const failed = quizReducer(createInitialState(), {
      type: "failed",
      message: "server down",
    });
    expect(failed.phase).toBe("failed");
    expect(failed.error).toBe("server down");

    const retried = quizReducer(failed, { type: "retry" });
    expect(retried.phase).toBe("submitting");
    expect(retried.error).toBe("");
  });

  it("retry only applies to a failed submission", () => {
    const initial = loaded();

    expect(quizReducer(initial, { type: "retry" })).toBe(initial);
  });

  it("ignores unknown actions", () => {
    const initial = createInitialState();

    expect(quizReducer(initial, { type: "nonsense" })).toBe(initial);
  });
});

describe("answeredCount", () => {
  it("counts questions left behind while answering", () => {
    const state = advance(draft(loaded(), "a"));

    expect(answeredCount(state)).toBe(1);
  });

  it("counts every question once the quiz has left the answering phase", () => {
    const state = quizReducer(loaded(), { type: "finish" });

    expect(answeredCount(state)).toBe(questions.length);
  });
});
