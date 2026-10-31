import { describe, expect, it } from "vitest";
import {
  formatCout,
  formatDate,
  formatDay,
  formatDurationMs,
  formatElapsed,
  formatUsd,
} from "./format";

describe("formatDurationMs", () => {
  it("returns a dash for null, negative or non-finite values", () => {
    expect(formatDurationMs(null)).toBe("—");
    expect(formatDurationMs(-1)).toBe("—");
    expect(formatDurationMs(Number.NaN, "fil")).toBe("—");
    expect(formatDurationMs(-5_000, "run")).toBe("—");
  });

  it("writes zero and under a minute", () => {
    expect(formatDurationMs(0)).toBe("0 s");
    expect(formatDurationMs(4_000)).toBe("4 s");
    expect(formatDurationMs(45_000, "fil")).toBe("45 s");
    expect(formatDurationMs(0, "run")).toBe("0m 00s");
    expect(formatDurationMs(45_000, "run")).toBe("0m 45s");
  });

  it("writes minutes in each notation", () => {
    expect(formatDurationMs(125_000)).toBe("2 min 05");
    expect(formatDurationMs(170_000, "fil")).toBe("2 min 50 s");
    expect(formatDurationMs(65_000, "run")).toBe("1m 05s");
  });

  it("writes an hour and more in each notation", () => {
    expect(formatDurationMs(3_900_000)).toBe("1 h 05");
    expect(formatDurationMs(3_900_000, "fil")).toBe("65 min 0 s");
    expect(formatDurationMs(3_900_000, "run")).toBe("65m 00s");
  });
});

describe("formatElapsed", () => {
  const now = Date.parse("2026-10-13T12:00:00Z");

  it("returns a dash when the start is unknown or unreadable", () => {
    expect(formatElapsed(null, now)).toBe("—");
    expect(formatElapsed("pas une date", now)).toBe("—");
  });

  it("never goes negative and says « < 1 min » under a minute", () => {
    expect(formatElapsed("2026-10-13T12:00:00Z", now)).toBe("< 1 min");
    expect(formatElapsed("2026-10-13T11:59:40Z", now)).toBe("< 1 min");
    expect(formatElapsed("2026-10-13T12:30:00Z", now)).toBe("< 1 min");
  });

  it("counts minutes, hours and days", () => {
    expect(formatElapsed("2026-10-13T11:45:00Z", now)).toBe("15 min");
    expect(formatElapsed("2026-10-13T09:55:00Z", now)).toBe("2 h 05");
    expect(formatElapsed("2026-10-11T08:00:00Z", now)).toBe("2 j 4 h");
  });
});

describe("formatDay", () => {
  it("keeps the UTC day whatever the local time zone", () => {
    expect(formatDay("2026-09-01")).toMatch(/^1 /);
  });
});

describe("formatDate", () => {
  it("writes day, month and hour of an ISO instant", () => {
    expect(formatDate("2026-10-14T12:00:00Z")).toMatch(/^14\/10\D+\d{2}:\d{2}$/);
  });
});

describe("formatUsd", () => {
  it("writes zero, cents, units and tens", () => {
    expect(formatUsd(0)).toBe("0 $");
    expect(formatUsd(0.004)).toBe("0.40 ¢");
    expect(formatUsd(0.42)).toBe("0.42 $");
    expect(formatUsd(12.4)).toBe("12 $");
  });

  it("returns a dash for a negative amount", () => {
    expect(formatUsd(-1)).toBe("—");
  });
});

describe("formatCout", () => {
  it("returns a dash for zero or a negative amount", () => {
    expect(formatCout(0)).toBe("—");
    expect(formatCout(-1)).toBe("—");
  });

  it("writes two decimals behind a dollar sign", () => {
    expect(formatCout(0.42)).toBe("$0.42");
    expect(formatCout(1.234)).toBe("$1.23");
  });
});
