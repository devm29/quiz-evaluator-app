/**
 * The two API calls this app makes.
 *
 * Kept free of React so they can be unit-tested directly and swapped for
 * another transport without touching the component.
 */

/** Thrown for any failed call; `status` is null for transport failures. */
export class QuizApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = "QuizApiError";
    this.status = status;
  }
}

const NETWORK_ERROR =
  "Unable to reach the quiz API. Check that it is running and try again.";

function apiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASEURL;
  if (!raw) {
    throw new QuizApiError("VITE_API_BASEURL is not configured");
  }
  // Tolerate a base URL given with or without a trailing slash.
  return raw.endsWith("/") ? raw : `${raw}/`;
}

async function request(path, init, fallbackMessage) {
  const url = `${apiBaseUrl()}${path}`;

  let response;
  try {
    response = await fetch(url, init);
  } catch {
    // fetch only rejects on a transport failure; a 4xx/5xx resolves normally.
    throw new QuizApiError(NETWORK_ERROR);
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    // A body that is not JSON (an HTML error page from a proxy, say) is not a
    // failure in itself; the status code below decides.
    payload = null;
  }

  if (!response.ok) {
    const message = (payload && (payload.msg || payload.detail)) || fallbackMessage;
    throw new QuizApiError(message, response.status);
  }

  return payload ?? {};
}

/**
 * GET the questions to ask. The API never sends the reference answers.
 *
 * @returns {Promise<Array<{id: number, questionText: string}>>}
 * @throws {QuizApiError} on a non-2xx response or a transport failure
 */
export async function fetchQuestions() {
  const payload = await request(
    "questions/",
    { headers: { Accept: "application/json" } },
    "Failed to load the quiz"
  );
  return Array.isArray(payload.questions) ? payload.questions : [];
}

/**
 * POST a completed quiz. The API marks it and returns the score.
 *
 * @param {{question: Array<{questionText: string, answerText: string}>, submittedBy: string}} quiz
 * @returns {Promise<{msg: string, quizId: number, score: number}>}
 * @throws {QuizApiError} on a non-2xx response or a transport failure
 */
export function submitQuiz(quiz) {
  return request(
    "submit_quiz/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: quiz }),
    },
    "Failed to submit quiz"
  );
}
