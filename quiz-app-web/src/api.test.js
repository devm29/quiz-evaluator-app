import { QuizApiError, fetchQuestions, submitQuiz } from "./api";

const QUIZ = { submittedBy: "test", question: [] };

function respond({ ok = true, status = 200, body = {} } = {}) {
  fetch.mockResolvedValueOnce({
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  });
}

beforeEach(() => {
  vi.stubEnv("VITE_API_BASEURL", "http://localhost:8221/");
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("submitQuiz", () => {
  it("posts the quiz wrapped in a data envelope", async () => {
    respond({ body: { msg: "ok", score: 3 } });

    const response = await submitQuiz(QUIZ);

    expect(fetch).toHaveBeenCalledWith("http://localhost:8221/submit_quiz/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: QUIZ }),
    });
    expect(response).toEqual({ msg: "ok", score: 3 });
  });

  it("tolerates a base URL without a trailing slash", async () => {
    vi.stubEnv("VITE_API_BASEURL", "http://localhost:8221");
    respond();

    await submitQuiz(QUIZ);

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8221/submit_quiz/",
      expect.anything()
    );
  });

  it("throws the API message when the server rejects the submission", async () => {
    respond({ ok: false, status: 400, body: { msg: "Missing required fields" } });

    await expect(submitQuiz(QUIZ)).rejects.toThrow("Missing required fields");
  });

  it("uses DRF's detail field when there is no msg", async () => {
    respond({ ok: false, status: 429, body: { detail: "Request was throttled." } });

    await expect(submitQuiz(QUIZ)).rejects.toThrow("Request was throttled.");
  });

  it("exposes the HTTP status on the thrown error", async () => {
    respond({ ok: false, status: 500, body: { msg: "boom" } });

    await expect(submitQuiz(QUIZ)).rejects.toMatchObject({
      name: "QuizApiError",
      status: 500,
    });
  });

  it("falls back to a generic message when the error body has no msg", async () => {
    respond({ ok: false, status: 502, body: {} });

    await expect(submitQuiz(QUIZ)).rejects.toThrow("Failed to submit quiz");
  });

  it("survives an error response that is not JSON", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: vi.fn().mockRejectedValue(new SyntaxError("not json")),
    });

    await expect(submitQuiz(QUIZ)).rejects.toThrow("Failed to submit quiz");
  });

  it("reports a friendly message when the API is unreachable", async () => {
    // Regression: a raw TypeError used to escape, so the user saw
    // "Failed to fetch".
    fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(submitQuiz(QUIZ)).rejects.toThrow(/Unable to reach the quiz API/);
  });

  it("fails clearly when the base URL is not configured", async () => {
    vi.stubEnv("VITE_API_BASEURL", "");

    await expect(submitQuiz(QUIZ)).rejects.toThrow(
      "VITE_API_BASEURL is not configured"
    );
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("fetchQuestions", () => {
  it("returns the question list from the API", async () => {
    const questions = [{ id: 1, questionText: "Why?" }];
    respond({ body: { questions } });

    await expect(fetchQuestions()).resolves.toEqual(questions);
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8221/questions/",
      expect.objectContaining({ headers: { Accept: "application/json" } })
    );
  });

  it("treats a body without a list as an empty quiz", async () => {
    respond({ body: {} });

    await expect(fetchQuestions()).resolves.toEqual([]);
  });

  it("has its own fallback message", async () => {
    respond({ ok: false, status: 503, body: null });

    await expect(fetchQuestions()).rejects.toThrow("Failed to load the quiz");
  });

  it("reports an unreachable API the same way as a submission", async () => {
    fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(fetchQuestions()).rejects.toThrow(/Unable to reach the quiz API/);
  });
});

test("QuizApiError defaults its status to null", () => {
  expect(new QuizApiError("nope").status).toBeNull();
});
