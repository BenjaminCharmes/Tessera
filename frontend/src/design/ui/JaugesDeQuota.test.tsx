import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import JaugesDeQuota from "./JaugesDeQuota";

const SEMAINE = { status: "allowed_warning", utilization: 0.88, resets_at: "2026-10-31T13:00:00Z", observed_at: "2026-10-30T14:00:00Z" };
const SESSION = { status: "allowed", utilization: 0.3, resets_at: "2026-10-30T18:00:00Z", observed_at: "2026-10-30T14:00:00Z" };

describe("JaugesDeQuota (ticket-726)", () => {
  it("shows the session and the week, the week in amber past 85 %", () => {
    render(<JaugesDeQuota fenetres={{ five_hour: SESSION, seven_day: SEMAINE }} />);

    const session = screen.getByText("Session (5 h)").closest("li") as HTMLElement;
    const semaine = screen.getByText("Semaine").closest("li") as HTMLElement;
    expect(within(session).getByText("30 %")).toBeInTheDocument();
    expect(within(semaine).getByText("88 %")).toBeInTheDocument();
    expect(semaine.querySelector(".bg-amber-400")).not.toBeNull();
    expect(session.querySelector(".bg-blue-400")).not.toBeNull();
  });

  it("says a window has no reading instead of showing 0 %", () => {
    render(<JaugesDeQuota fenetres={undefined} />);

    expect(screen.getAllByText("pas de relevé")).toHaveLength(2);
    expect(screen.queryByText("0 %")).toBeNull();
  });
});
