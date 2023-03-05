import {
  answeredCount,
  createInitialState,
  quizReducer,
} from "./quizReducer";
import questions from "../constants/constants";

const draft = (state, value) => quizReducer(state, { type: "draft", value });
const advance = (state) => quizReducer(state, { type: "advance" });

describe("quizReducer", () => {
  it("starts on the first question with no answers recorded", () => {
    const state = createInitialState();

    expect(state.index).toBe(0);
    expect(state.phase).toBe("answering");
    expect(state.answers).toHaveLength(questions.length);
    expect(state.answers.every((answer) => answer.answerText === "")).toBe(true);
  });

  it("does not mutate the shared question constants", () => {
    const state = advance(draft(createInitialState(), "mutated"));

    expect(state.answers[0].answerText).toBe("mutated");
    expect(questions[0].answerText).toBe("");
  });

  it("records the draft against the current question and clears it", () => {
    const state = advance(draft(createInitialState(), "my answer"));

    expect(state.answers[0].answerText).toBe("my answer");
    expect(state.index).toBe(1);
    expect(state.draft).toBe("");
  });

  it("moves to submitting after the last question", () => {
    let state = createInitialState();
    for (let i = 0; i < questions.length; i += 1) {
      state = advance(draft(state, `a${i}`));
    }

    expect(state.phase).toBe("submitting");
    expect(state.answers.map((a) => a.answerText)).toEqual(
      questions.map((_, i) => `a${i}`)
    );
  });

  it("advancing while submitting is a no-op", () => {
    let state = createInitialState();
    for (let i = 0; i < questions.length; i += 1) {
      state = advance(draft(state, "x"));
    }

    expect(advance(state)).toBe(state);
    expect(draft(state, "late")).toBe(state);
  });

  it("finish submits partial answers from the current question", () => {
    let state = advance(draft(createInitialState(), "first"));
    state = draft(state, "second, unsent");
    state = quizReducer(state, { type: "finish" });

    expect(state.phase).toBe("submitting");
    expect(state.answers[0].answerText).toBe("first");
    expect(state.answers[1].answerText).toBe("second, unsent");
    expect(state.answers[2].answerText).toBe("");
  });

  it("finish after submission is a no-op", () => {
    const submitted = quizReducer(createInitialState(), { type: "submitted" });

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
    const initial = createInitialState();

    expect(quizReducer(initial, { type: "retry" })).toBe(initial);
  });

  it("ignores unknown actions", () => {
    const initial = createInitialState();

    expect(quizReducer(initial, { type: "nonsense" })).toBe(initial);
  });
});

describe("answeredCount", () => {
  it("counts questions left behind while answering", () => {
    const state = advance(draft(createInitialState(), "a"));

    expect(answeredCount(state)).toBe(1);
  });

  it("counts every question once the quiz has left the answering phase", () => {
    const state = quizReducer(createInitialState(), { type: "finish" });

    expect(answeredCount(state)).toBe(questions.length);
  });
});
