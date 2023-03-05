import { render, screen } from "@testing-library/react";

import App from "./App";
import questions from "./constants/constants";

jest.mock("./routes/api", () => ({ QuizPost: jest.fn() }));

test("routes / to the quiz and renders the first question", () => {
  render(<App />);

  expect(screen.getByText(questions[0].questionText)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});
