import { render, screen } from "@testing-library/react";

import App from "./App.jsx";
import questions from "./constants/constants";

vi.mock("./api", () => ({ QuizPost: vi.fn() }));

test("renders the quiz on its first question", () => {
  render(<App />);

  expect(screen.getByText(questions[0].questionText)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});
