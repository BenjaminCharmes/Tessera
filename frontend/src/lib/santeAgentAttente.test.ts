import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { santeAgent } from "./santeAgent";

const DERNIER = "2026-10-23T10:00:00.000Z";
const T0 = Date.parse(DERNIER);

describe("santeAgent with an external wait (ticket-564)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("is never a suspected stall after more than 180 seconds of silence", () => {
    vi.setSystemTime(T0 + 600_000);

    expect(santeAgent(DERNIER, Date.now(), null, true)).toBe("attente");
  });

  it("stays a suspected stall after 181 seconds without a wait", () => {
    vi.setSystemTime(T0 + 181_000);

    expect(santeAgent(DERNIER, Date.now(), null)).toBe("blocage_suspecte");
    expect(santeAgent(DERNIER, Date.now(), null, false)).toBe("blocage_suspecte");
  });

  it("lets a pending question win over the wait", () => {
    expect(santeAgent(DERNIER, T0 + 600_000, "On casse l'API ?", true)).toBe("question");
  });
});
