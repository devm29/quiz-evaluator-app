/**
 * The shipped quiz.
 *
 * The API has no endpoint that serves questions, so the client carries its own
 * copy. Keep this in step with `quiz_app_api/quiz/fixtures_data.py`, which is
 * what the reference answers are seeded from.
 */
const questions = [
  { questionText: "Which planet is known as the Red Planet?", answerText: "" },
  { questionText: "What is the chemical symbol for gold?", answerText: "" },
  { questionText: "How many sides does a hexagon have?", answerText: "" },
  { questionText: "What is the largest ocean on Earth?", answerText: "" },
  { questionText: "In which city is the Colosseum?", answerText: "" },
];

/** Milliseconds a candidate gets on any single question before it auto-advances. */
export const QUESTION_TIME_LIMIT_MS = 3 * 60 * 1000;

/** Milliseconds for the whole attempt, shown by the countdown in the header. */
export const QUIZ_TIME_LIMIT_MS = questions.length * QUESTION_TIME_LIMIT_MS;

export default questions;
