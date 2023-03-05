/**
 * The shipped quiz.
 *
 * The API has no endpoint that serves questions, so the client carries its own
 * copy. Keep this in step with `quiz_app_api/quiz/fixtures_data.py`, which is
 * what the reference answers are seeded from.
 */
const questions = [
  { questionText: "Is Milkyway the biggest galaxy in Universe?", answerText: "" },
  { questionText: "Cactus is a flower?(Yes/No)", answerText: "" },
  { questionText: "Is Tokyo the capital of Japan?(Yes/No)", answerText: "" },
  {
    questionText: "Is China the most populated country in the world?(Yes/No)",
    answerText: "",
  },
  { questionText: "Algae is a plant?(Yes/No)", answerText: "" },
];

/** Milliseconds a candidate gets on any single question before it auto-advances. */
export const QUESTION_TIME_LIMIT_MS = 3 * 60 * 1000;

/** Milliseconds for the whole attempt, shown by the countdown in the header. */
export const QUIZ_TIME_LIMIT_MS = questions.length * QUESTION_TIME_LIMIT_MS;

export default questions;
