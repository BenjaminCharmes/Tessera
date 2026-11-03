import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { applyEvent } from "../../hooks/streamState";
import { api } from "../../lib/api";
import { DUREE_DE_LA_BULLE_MS } from "../../lib/bureau/bulleDOutil";
import type { AgentRole, OrchestratorEvent } from "../../types/api";
import Piece from "./Piece";
import { DERNIER, T0, etatEnCodage } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function appelDOutil(agent: AgentRole, data: Record<string, unknown>): OrchestratorEvent {
  return { type: "agent_tool_use", agent, ticket_id: "ticket-001", data, timestamp: DERNIER };
}

const LECTURE = { tool: "Read", input: { file_path: "C:\\Users\\jdupont\\ide-core\\conflits.py" } };

describe("Piece tool bubble", () => {
  it("shows what the working agent does above its desk after a tool use", () => {
    const etat = applyEvent(etatEnCodage(), appelDOutil("codeur", LECTURE));
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    const bulle = screen.getByTestId("bulle-outil");
    expect(bulle).toHaveTextContent("lit conflits.py");
    expect(bulle.textContent).not.toContain("Users");
  });

  it("removes the bubble 10 s after the last tool use", () => {
    const etat = applyEvent(etatEnCodage(), appelDOutil("codeur", LECTURE));
    const { rerender } = render(
      <Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_BULLE_MS - 1} />,
    );
    expect(screen.getByTestId("bulle-outil")).toBeInTheDocument();

    rerender(<Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_BULLE_MS} />);

    expect(screen.queryByTestId("bulle-outil")).toBeNull();
  });

  it("draws no bubble before any tool use", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 1_000} />);

    expect(screen.queryByTestId("bulle-outil")).toBeNull();
  });

  it("draws no bubble for a desk that is not occupied", () => {
    // Le reviewer n'a pas démarré : son poste est libre, la bulle ne s'y pose pas.
    const etat = applyEvent(etatEnCodage(), appelDOutil("reviewer", LECTURE));
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    expect(screen.queryByTestId("bulle-outil")).toBeNull();
  });

  it("truncates a long phrase", () => {
    const longue = { tool: "Edit", input: { file_path: "src/un-nom-de-fichier-vraiment-tres-long.tsx" } };
    const etat = applyEvent(etatEnCodage(), appelDOutil("codeur", longue));
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    const texte = screen.getByTestId("bulle-outil").textContent ?? "";
    expect(texte).toHaveLength(32);
    expect(texte.endsWith("…")).toBe(true);
  });
});
