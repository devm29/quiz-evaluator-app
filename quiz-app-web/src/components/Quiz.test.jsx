import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import Quiz from "./Quiz.jsx";
import questions, { QUESTION_TIME_LIMIT_MS } from "../constants/constants";
import { QuizPost } from "../api";

vi.mock("react-countdown", () => ({
  default: ({ onComplete }) => (
    <button type="button" onClick={onComplete}>
      expire-countdown
    </button>
  ),
}));
vi.mock("../api", () => ({ QuizPost: vi.fn() }));

const answerField = () => screen.getByLabelText("Your answer");
const type = (value) => fireEvent.change(answerField(), { target: { value } });
const clickButton = (name) =>
  fireEvent.click(screen.getByRole("button", { name }));

function answerAll(answers) {
  answers.forEach((answer, index) => {
    type(answer);
    clickButton(index === answers.length - 1 ? "Submit" : "Next");
  });
}

describe("Quiz component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    QuizPost.mockResolvedValue({ msg: "saved" });
  });

  it("walks through every question and submits the collected answers", async () => {
    render(<Quiz />);
    expect(screen.getByText(questions[0].questionText)).toBeInTheDocument();

    answerAll(questions.map((_, index) => `answer-${index}`));

    await screen.findByText("Thank you for taking this quiz.");
    expect(QuizPost).toHaveBeenCalledTimes(1);
    expect(QuizPost).toHaveBeenCalledWith({
      submittedBy: "",
      question: questions.map((question, index) => ({
        questionText: question.questionText,
        answerText: `answer-${index}`,
      })),
    });
  });

  it("shows progress through the quiz", () => {
    render(<Quiz />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");

    clickButton("Next");

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
    expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
  });

  it("clears the input between questions", () => {
    render(<Quiz />);

    type("first answer");
    clickButton("Next");

    expect(answerField()).toHaveValue("");
  });

  it("advances on Enter as well as the button", () => {
    render(<Quiz />);

    type("typed");
    fireEvent.keyDown(answerField(), { key: "Enter" });

    expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
  });

  it("labels the final question's control Submit", () => {
    render(<Quiz />);

    for (let index = 0; index < questions.length - 1; index += 1) {
      clickButton("Next");
    }

    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
  });

  it("surfaces the API error and lets the candidate retry", async () => {
    QuizPost.mockRejectedValueOnce(new Error("Missing required fields"));
    render(<Quiz />);

    answerAll(questions.map(() => "x"));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Missing required fields"
      )
    );
    expect(
      screen.queryByText("Thank you for taking this quiz.")
    ).not.toBeInTheDocument();

    clickButton("Try again");

    await screen.findByText("Thank you for taking this quiz.");
    expect(QuizPost).toHaveBeenCalledTimes(2);
  });

  it("submits only once even if the candidate keeps clicking", async () => {
    let resolveSubmit;
    QuizPost.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSubmit = resolve;
        })
    );
    render(<Quiz />);

    answerAll(questions.map(() => "x"));

    // The submit control is gone while the request is in flight, so there is
    // nothing left to double-click.
    expect(
      screen.queryByRole("button", { name: "Submit" })
    ).not.toBeInTheDocument();
    expect(screen.getByText("Submitting your answers…")).toBeInTheDocument();

    await act(async () => {
      resolveSubmit({ msg: "saved" });
    });
    expect(QuizPost).toHaveBeenCalledTimes(1);
  });

  it("submits whatever has been answered when the overall timer expires", async () => {
    render(<Quiz />);

    type("partial");
    clickButton("expire-countdown");

    await waitFor(() => expect(QuizPost).toHaveBeenCalledTimes(1));
    const [submission] = QuizPost.mock.calls[0];
    expect(submission.question[0].answerText).toBe("partial");
    expect(submission.question[1].answerText).toBe("");
  });

  it("hides the countdown once the quiz has been submitted", async () => {
    render(<Quiz />);

    answerAll(questions.map(() => "x"));

    await screen.findByText("Thank you for taking this quiz.");
    expect(
      screen.queryByRole("button", { name: "expire-countdown" })
    ).not.toBeInTheDocument();
  });

  describe("per-question time limit", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      // Discard rather than run: firing a pending timer here would queue a
      // React update outside act().
      vi.clearAllTimers();
      vi.useRealTimers();
    });

    it("auto-advances when a question's time runs out", () => {
      render(<Quiz />);

      type("slow answer");
      act(() => {
        vi.advanceTimersByTime(QUESTION_TIME_LIMIT_MS);
      });

      expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
    });

    it("keeps the answer that was on screen when time ran out", async () => {
      render(<Quiz />);

      type("slow answer");
      // Each expiry is a separate render, so the next question's timer is
      // only scheduled once React has flushed the previous one.
      for (let index = 0; index < questions.length; index += 1) {
        act(() => {
          vi.advanceTimersByTime(QUESTION_TIME_LIMIT_MS);
        });
      }

      // RTL's waitFor polls on timers, which are faked here.
      expect(QuizPost).toHaveBeenCalledTimes(1);
      expect(QuizPost.mock.calls[0][0].question[0].answerText).toBe(
        "slow answer"
      );
    });

    it("typing does not restart the question clock", () => {
      // Regression: the timer effect used to depend on the draft answer, so
      // every keystroke bought another full three minutes.
      render(<Quiz />);

      act(() => {
        vi.advanceTimersByTime(QUESTION_TIME_LIMIT_MS - 1000);
      });
      type("a late keystroke");
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
    });
  });
});
