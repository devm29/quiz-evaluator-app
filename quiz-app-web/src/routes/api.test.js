import { QuizApiError, QuizPost } from "./api";

const QUIZ = { submittedBy: "test", question: [] };

describe("QuizPost", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv, REACT_APP_API_BASEURL: "http://localhost:8221/" };
    global.fetch = jest.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    jest.resetAllMocks();
  });

  function respond({ ok = true, status = 200, body = {} } = {}) {
    fetch.mockResolvedValueOnce({
      ok,
      status,
      json: jest.fn().mockResolvedValue(body),
    });
  }

  it("posts the quiz wrapped in a data envelope", async () => {
    respond({ body: { msg: "ok" } });

    const response = await QuizPost(QUIZ);

    expect(fetch).toHaveBeenCalledWith("http://localhost:8221/submit_quiz/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: QUIZ }),
    });
    expect(response).toEqual({ msg: "ok" });
  });

  it("tolerates a base URL without a trailing slash", async () => {
    process.env.REACT_APP_API_BASEURL = "http://localhost:8221";
    respond();

    await QuizPost(QUIZ);

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8221/submit_quiz/",
      expect.anything()
    );
  });

  it("throws the API message when the server rejects the submission", async () => {
    respond({ ok: false, status: 400, body: { msg: "Missing required fields" } });

    await expect(QuizPost(QUIZ)).rejects.toThrow("Missing required fields");
  });

  it("exposes the HTTP status on the thrown error", async () => {
    respond({ ok: false, status: 500, body: { msg: "boom" } });

    await expect(QuizPost(QUIZ)).rejects.toMatchObject({
      name: "QuizApiError",
      status: 500,
    });
  });

  it("falls back to a generic message when the error body has no msg", async () => {
    respond({ ok: false, status: 502, body: {} });

    await expect(QuizPost(QUIZ)).rejects.toThrow("Failed to submit quiz");
  });

  it("survives an error response that is not JSON", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: jest.fn().mockRejectedValue(new SyntaxError("not json")),
    });

    await expect(QuizPost(QUIZ)).rejects.toThrow("Failed to submit quiz");
  });

  it("reports a friendly message when the API is unreachable", async () => {
    // Regression: the previous implementation rethrew the raw TypeError, so
    // this message was unreachable and the user saw "Failed to fetch".
    fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(QuizPost(QUIZ)).rejects.toThrow(/Unable to reach the quiz API/);
  });

  it("fails clearly when the base URL is not configured", async () => {
    delete process.env.REACT_APP_API_BASEURL;

    await expect(QuizPost(QUIZ)).rejects.toThrow(
      "REACT_APP_API_BASEURL is not configured"
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("QuizApiError defaults its status to null", () => {
    expect(new QuizApiError("nope").status).toBeNull();
  });
});
