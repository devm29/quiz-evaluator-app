/**
 * The single API call this app makes.
 *
 * Kept free of React so it can be unit-tested directly and swapped for another
 * transport without touching the component.
 */

/** Thrown for any failed submission; `status` is null for transport failures. */
export class QuizApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = "QuizApiError";
    this.status = status;
  }
}

const DEFAULT_ERROR = "Failed to submit quiz";
const NETWORK_ERROR =
  "Unable to reach the quiz API. Check that it is running and try again.";

function apiBaseUrl() {
  const raw = process.env.REACT_APP_API_BASEURL;
  if (!raw) {
    throw new QuizApiError("REACT_APP_API_BASEURL is not configured");
  }
  // Tolerate a base URL given with or without a trailing slash.
  return raw.endsWith("/") ? raw : `${raw}/`;
}

/**
 * POST a completed quiz.
 *
 * @param {{question: Array, submittedBy: string, evaluatedBy: string, score: number}} quiz
 * @returns {Promise<object>} the parsed response body
 * @throws {QuizApiError} on a non-2xx response or a transport failure
 */
export async function QuizPost(quiz) {
  const url = `${apiBaseUrl()}submit_quiz/`;

  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: quiz }),
    });
  } catch {
    // fetch only rejects on a transport failure; a 4xx/5xx resolves normally.
    // The previous implementation wrapped both in one try block and rethrew
    // anything that was an Error, which made this message unreachable.
    throw new QuizApiError(NETWORK_ERROR);
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // A body that is not JSON (an HTML error page from a proxy, say) is not a
    // failure in itself; the status code below decides.
    payload = null;
  }

  if (!response.ok) {
    const message =
      (payload && (payload.msg || payload.detail)) || DEFAULT_ERROR;
    throw new QuizApiError(message, response.status);
  }

  return payload ?? {};
}
