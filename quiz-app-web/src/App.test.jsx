import { fireEvent, render, screen } from "@testing-library/react";

import App from "./App.jsx";
import { QUESTIONS } from "./test/questions";

vi.mock("./api", () => ({
  fetchQuestions: vi.fn(() => Promise.resolve(QUESTIONS)),
  submitQuiz: vi.fn(),
}));

test("loads the quiz from the API and starts on the first question", async () => {
  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: "Start the quiz" }));

  expect(screen.getByText(QUESTIONS[0].questionText)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});
