import { formatClock } from "./clock";

describe("formatClock", () => {
  it("pads seconds but not minutes", () => {
    expect(formatClock({ minutes: 9, seconds: 5 })).toBe("9:05");
  });

  it("folds hours into minutes", () => {
    expect(formatClock({ hours: 1, minutes: 2, seconds: 30 })).toBe("62:30");
  });

  it("shows zero when time is up", () => {
    expect(formatClock({})).toBe("0:00");
  });
});
