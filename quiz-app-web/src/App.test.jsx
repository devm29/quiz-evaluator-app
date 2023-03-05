import { render, screen } from "@testing-library/react";

import App from "./App.jsx";
import { QUESTIONS } from "./test/questions";

vi.mock("./api", () => ({
  fetchQuestions: vi.fn(() => Promise.resolve(QUESTIONS)),
  submitQuiz: vi.fn(),
}));

test("loads the quiz from the API and shows the first question", async () => {
  render(<App />);

  expect(await screen.findByText(QUESTIONS[0].questionText)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});
