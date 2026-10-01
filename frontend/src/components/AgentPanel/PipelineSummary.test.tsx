import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import PipelineSummary from "./PipelineSummary";

describe("PipelineSummary — ticket-282", () => {
  it("l'icône et le titre du run approuvé sont dans un même conteneur flex", () => {
    const result = {
      ticket_id: "ticket-001",
      final_status: "done" as const,
      rounds: 1,
      approved: true,
    };

    const { container } = render(<PipelineSummary result={result} />);

    // La div de titre doit être flex pour que l'icône SVG reste inline
    // avec le texte (Tailwind v4 rend les SVG en display:block sinon).
    const titreDiv = container.querySelector(
      ".font-semibold.flex, .font-semibold.inline-flex",
    );
    expect(titreDiv).not.toBeNull();
    expect(titreDiv?.textContent).toContain("Pipeline terminé");
  });

  it("l'icône et le titre du run non approuvé sont dans un même conteneur flex", () => {
    const result = {
      ticket_id: "ticket-002",
      final_status: "blocked" as const,
      rounds: 2,
      approved: false,
    };

    const { container } = render(<PipelineSummary result={result} />);

    const titreDiv = container.querySelector(
      ".font-semibold.flex, .font-semibold.inline-flex",
    );
    expect(titreDiv).not.toBeNull();
    expect(titreDiv?.textContent).toContain("Non approuvé");
  });
});
