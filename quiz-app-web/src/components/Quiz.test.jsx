import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import Quiz from "./Quiz.jsx";
import { QUESTION_TIME_LIMIT_MS } from "../constants/constants";
import { fetchQuestions, submitQuiz } from "../api";
import { QUESTIONS as questions } from "../test/questions";

vi.mock("react-countdown", () => ({
  default: ({ onComplete }) => (
    <button type="button" onClick={onComplete}>
      expire-countdown
    </button>
  ),
}));
vi.mock("../api", () => ({ fetchQuestions: vi.fn(), submitQuiz: vi.fn() }));

const answerField = () => screen.getByLabelText("Your answer");
const type = (value) => fireEvent.change(answerField(), { target: { value } });
const clickButton = (name) =>
  fireEvent.click(screen.getByRole("button", { name }));

// Resolves the mocked questions fetch without polling, so it also works
// while timers are faked.
async function loadQuiz() {
  render(<Quiz />);
  await act(async () => {});
}

async function renderQuiz() {
  await loadQuiz();
  clickButton("Start the quiz");
}

function answerAll(answers) {
  answers.forEach((answer, index) => {
    type(answer);
    clickButton(index === answers.length - 1 ? "Submit" : "Next");
  });
}

describe("loading the quiz", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state until the questions arrive", async () => {
    let resolveQuestions;
    fetchQuestions.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveQuestions = resolve;
      })
    );
    render(<Quiz />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading the questions");
    expect(screen.queryByLabelText("Your answer")).not.toBeInTheDocument();

    await act(async () => resolveQuestions(questions));

    expect(screen.getByRole("button", { name: "Start the quiz" })).toBeInTheDocument();
  });

  it("explains a failed load and loads again on request", async () => {
    fetchQuestions
      .mockRejectedValueOnce(new Error("Unable to reach the quiz API."))
      .mockResolvedValueOnce(questions);
    await loadQuiz();

    expect(screen.getByRole("alert")).toHaveTextContent("Unable to reach the quiz API.");

    clickButton("Try again");
    await act(async () => {});

    expect(fetchQuestions).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Start the quiz" })).toBeInTheDocument();
  });

  it("says so when the API has no questions", async () => {
    fetchQuestions.mockResolvedValueOnce([]);
    await loadQuiz();

    expect(screen.getByRole("alert")).toHaveTextContent("There are no questions yet");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "0");
  });

  it("asks the questions in the order the API sent them", async () => {
    fetchQuestions.mockResolvedValueOnce([...questions].reverse());
    await renderQuiz();

    expect(screen.getByText(questions.at(-1).questionText)).toBeInTheDocument();
    expect(screen.getByText(`of ${questions.length}`, { exact: false })).toBeInTheDocument();
  });
});

describe("start screen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchQuestions.mockResolvedValue(questions);
    submitQuiz.mockResolvedValue({ msg: "saved", score: 2 });
  });

  it("says how long the quiz is before the clock starts", async () => {
    await loadQuiz();

    expect(
      screen.getByRole("heading", { name: `${questions.length} questions, 3 minutes each` })
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "expire-countdown" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Your answer")).not.toBeInTheDocument();
  });

  it("starts on Enter in the name field as well as the button", async () => {
    await loadQuiz();

    fireEvent.submit(screen.getByLabelText(/Your name/));

    expect(screen.getByText(questions[0].questionText)).toBeInTheDocument();
  });

  it("sends the trimmed name and shows the mark the API returned", async () => {
    await loadQuiz();
    fireEvent.change(screen.getByLabelText(/Your name/), {
      target: { value: "  Sam Rivera " },
    });
    clickButton("Start the quiz");

    answerAll(questions.map(() => "x"));

    expect(await screen.findByText("Thank you, Sam Rivera.")).toBeInTheDocument();
    expect(screen.getByText(`You scored 2 out of ${questions.length}.`)).toBeInTheDocument();
    expect(submitQuiz.mock.calls[0][0].submittedBy).toBe("Sam Rivera");
  });

  it("caps the name at what the API accepts", async () => {
    await loadQuiz();

    expect(screen.getByLabelText(/Your name/)).toHaveAttribute("maxLength", "150");
  });
});

describe("Quiz component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchQuestions.mockResolvedValue(questions);
    submitQuiz.mockResolvedValue({ msg: "saved" });
  });

  it("walks through every question and submits the collected answers", async () => {
    await renderQuiz();
    expect(screen.getByText(questions[0].questionText)).toBeInTheDocument();

    answerAll(questions.map((_, index) => `answer-${index}`));

    await screen.findByText("Thank you for taking this quiz.");
    expect(submitQuiz).toHaveBeenCalledTimes(1);
    expect(submitQuiz).toHaveBeenCalledWith({
      submittedBy: "",
      question: questions.map((question, index) => ({
        questionText: question.questionText,
        answerText: `answer-${index}`,
      })),
    });
  });

  it("shows progress through the quiz", async () => {
    await renderQuiz();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");

    clickButton("Next");

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
    expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
  });

  it("clears the input between questions", async () => {
    await renderQuiz();

    type("first answer");
    clickButton("Next");

    expect(answerField()).toHaveValue("");
  });

  it("advances on Enter as well as the button", async () => {
    await renderQuiz();

    type("typed");
    fireEvent.keyDown(answerField(), { key: "Enter" });

    expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
  });

  it("labels the final question's control Submit", async () => {
    await renderQuiz();

    for (let index = 0; index < questions.length - 1; index += 1) {
      clickButton("Next");
    }

    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
  });

  it("surfaces the API error and lets the candidate retry", async () => {
    submitQuiz.mockRejectedValueOnce(new Error("Missing required fields"));
    await renderQuiz();

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
    expect(submitQuiz).toHaveBeenCalledTimes(2);
  });

  it("submits only once even if the candidate keeps clicking", async () => {
    let resolveSubmit;
    submitQuiz.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSubmit = resolve;
        })
    );
    await renderQuiz();

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
    expect(submitQuiz).toHaveBeenCalledTimes(1);
  });

  it("submits whatever has been answered when the overall timer expires", async () => {
    await renderQuiz();

    type("partial");
    clickButton("expire-countdown");

    await waitFor(() => expect(submitQuiz).toHaveBeenCalledTimes(1));
    const [submission] = submitQuiz.mock.calls[0];
    expect(submission.question[0].answerText).toBe("partial");
    expect(submission.question[1].answerText).toBe("");
  });

  it("hides the countdown once the quiz has been submitted", async () => {
    await renderQuiz();

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

    it("auto-advances when a question's time runs out", async () => {
      await renderQuiz();

      type("slow answer");
      act(() => {
        vi.advanceTimersByTime(QUESTION_TIME_LIMIT_MS);
      });

      expect(screen.getByText(questions[1].questionText)).toBeInTheDocument();
    });

    it("keeps the answer that was on screen when time ran out", async () => {
      await renderQuiz();

      type("slow answer");
      // Each expiry is a separate render, so the next question's timer is
      // only scheduled once React has flushed the previous one.
      for (let index = 0; index < questions.length; index += 1) {
        act(() => {
          vi.advanceTimersByTime(QUESTION_TIME_LIMIT_MS);
        });
      }

      // RTL's waitFor polls on timers, which are faked here.
      expect(submitQuiz).toHaveBeenCalledTimes(1);
      expect(submitQuiz.mock.calls[0][0].question[0].answerText).toBe(
        "slow answer"
      );
    });

    it("typing does not restart the question clock", async () => {
      // Regression: the timer effect used to depend on the draft answer, so
      // every keystroke bought another full three minutes.
      await renderQuiz();

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
