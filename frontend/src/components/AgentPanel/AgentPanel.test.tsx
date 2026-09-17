import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import RoundBadge from "./RoundBadge";
import PipelineSummary from "./PipelineSummary";
import TokenStream from "./TokenStream";
import AgentBlock from "./AgentBlock";
import type { PipelineResult } from "../../types/api";

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = () => {};
});

const APPROVED: PipelineResult = {
  ticket_id: "ticket-001",
  final_status: "done",
  rounds: 2,
  approved: true,
};

const REJECTED: PipelineResult = {
  ticket_id: "ticket-002",
  final_status: "todo",
  rounds: 3,
  approved: false,
};

describe("RoundBadge", () => {
  it("renders current round and default max", () => {
    render(<RoundBadge current={1} />);
    expect(screen.getByText("Tour 1 / 3")).toBeTruthy();
  });

  it("renders custom max", () => {
    render(<RoundBadge current={2} max={5} />);
    expect(screen.getByText("Tour 2 / 5")).toBeTruthy();
  });
});

describe("PipelineSummary", () => {
  it("shows approved message when approved", () => {
    render(<PipelineSummary result={APPROVED} />);
    expect(screen.getByText(/Pipeline terminé/)).toBeTruthy();
    expect(screen.getByText("ticket-001")).toBeTruthy();
    expect(screen.getByText("done")).toBeTruthy();
  });

  it("shows rejected message when not approved", () => {
    render(<PipelineSummary result={REJECTED} />);
    expect(screen.getByText(/Non approuvé/)).toBeTruthy();
  });

  it("shows duration when provided", () => {
    render(<PipelineSummary result={APPROVED} durationMs={5000} />);
    expect(screen.getByText("5s")).toBeTruthy();
  });

  it("hides duration when not provided", () => {
    render(<PipelineSummary result={APPROVED} />);
    expect(screen.queryByText(/Durée/)).toBeNull();
  });
});

describe("TokenStream", () => {
  it("renders tokens", () => {
    render(<TokenStream tokens="hello world" isActive={false} />);
    expect(screen.getByText("hello world")).toBeTruthy();
  });

  it("shows cursor when active", () => {
    // Le curseur est un bloc dessiné depuis ticket-067 : il n'a plus de
    // contenu textuel, donc on l'observe par sa classe d'animation.
    const { container } = render(<TokenStream tokens="typing…" isActive={true} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("hides cursor when inactive", () => {
    render(<TokenStream tokens="done" isActive={false} />);
    expect(screen.queryByText("█")).toBeNull();
  });
});

describe("AgentBlock", () => {
  it("renders codeur label", () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens="some code"
        isActive={false}
        isDone={true}
      />,
    );
    expect(screen.getByText(/CODEUR/)).toBeTruthy();
  });

  it("shows done when isDone and not active", () => {
    render(
      <AgentBlock agent="codeur" tokens="" isActive={false} isDone={true} />,
    );
    expect(screen.getByText("done")).toBeTruthy();
  });

  it("shows generating placeholder when active with no tokens", () => {
    render(
      <AgentBlock agent="codeur" tokens="" isActive={true} isDone={false} />,
    );
    expect(screen.getByText(/Generating/i)).toBeTruthy();
  });

  it("renders reviewer label and verdict", () => {
    render(
      <AgentBlock
        agent="reviewer"
        tokens=""
        isActive={false}
        isDone={true}
        reviewContent="APPROVED: looks good"
      />,
    );
    expect(screen.getByText(/REVIEWER/)).toBeTruthy();
    expect(screen.getByText(/APPROVED/)).toBeTruthy();
  });

  it("uses agent name as fallback label for unknown roles", () => {
    render(
      <AgentBlock
        agent={"testeur" as "codeur"}
        tokens=""
        isActive={false}
        isDone={false}
      />,
    );
    expect(screen.getByText("TESTEUR")).toBeTruthy();
  });
});
