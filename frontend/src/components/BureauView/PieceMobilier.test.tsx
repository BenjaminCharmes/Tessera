import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { api } from "../../lib/api";
import { imageDuCadre } from "../../lib/bureau/cadre";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import Piece from "./Piece";
import Salle from "./Salle";
import { T0 } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function ev(
  type: EventType,
  agent: AgentRole | null = null,
  data: Record<string, unknown> = {},
  ticket = "ticket-001",
): OrchestratorEvent {
  return { type, agent, ticket_id: ticket, data, timestamp: "2026-10-29T09:00:00.000Z" };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const refus = () =>
  ev("agent_done", "reviewer", { content: "CHANGES_REQUESTED\n- un test manque", verdict: "CHANGES_REQUESTED" });

function aLHeure(heure: number): number {
  return new Date(2026, 9, 29, heure, 0).getTime();
}

function aiguille(racine: HTMLElement, laquelle: "heure" | "minute"): string | null {
  return racine.querySelector(`[data-sprite="horloge"] [data-aiguille="${laquelle}"]`)?.getAttribute("data-angle") ?? null;
}

function boules(racine: HTMLElement): number {
  return racine.querySelectorAll('[data-sprite="corbeille"] [data-detail="boule-de-papier"]').length;
}

function imageDuCadreDessine(racine: HTMLElement): string | null {
  return racine.querySelector('[data-sprite="cadre"]')?.getAttribute("data-image") ?? null;
}

describe("the wall clock", () => {
  it("places the hands of a project room by the hour of the view clock", () => {
    const a3 = render(<Piece projet="ide-core" etat={INITIAL} maintenant={aLHeure(3)} />).container;
    const a9 = render(<Piece projet="ide-core" etat={INITIAL} maintenant={aLHeure(9)} />).container;

    expect(aiguille(a3, "heure")).toBe("90");
    expect(aiguille(a9, "heure")).toBe("270");
    expect(aiguille(a3, "heure")).not.toBe(aiguille(a9, "heure"));
  });

  it("hangs one in a common room too, on the same clock", () => {
    const { container } = render(
      <Salle titre="Salle de test" entete="x" vide="Personne" mobilier={<svg />} maintenant={aLHeure(9)} />,
    );

    expect(aiguille(container, "heure")).toBe("270");
    expect(container.querySelector('[data-sprite="cadre"]')).not.toBeNull();
  });
});

describe("the frame", () => {
  const PROJETS = ["ide-core", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"];

  it("hangs different pictures in two different projects", () => {
    const paire = PROJETS.flatMap((a) => PROJETS.map((b) => [a, b] as const)).find(
      ([a, b]) => imageDuCadre(a) !== imageDuCadre(b),
    );
    expect(paire).toBeDefined();
    const [a, b] = paire ?? ["", ""];

    const pieceA = render(<Piece projet={a} etat={INITIAL} maintenant={T0} />).container;
    const pieceB = render(<Piece projet={b} etat={INITIAL} maintenant={T0} />).container;

    expect(imageDuCadreDessine(pieceA)).not.toBeNull();
    expect(imageDuCadreDessine(pieceA)).not.toBe(imageDuCadreDessine(pieceB));
  });

  it("keeps the same picture for a project from one render to the next", () => {
    const premier = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />).container;
    const second = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0 + 3_600_000} />).container;

    expect(imageDuCadreDessine(premier)).toBe(imageDuCadreDessine(second));
  });
});

describe("the shelf", () => {
  it("is drawn in a project room, with no state", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(container.querySelectorAll('[data-sprite="etagere"]')).toHaveLength(1);
  });
});

describe("the bin", () => {
  it("is drawn empty when the reviewer refused nothing", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(container.querySelectorAll('[data-sprite="corbeille"]')).toHaveLength(1);
    expect(boules(container)).toBe(0);
  });

  it("holds one ball per refusal of the reviewer on the current ticket", () => {
    const un = render(<Piece projet="ide-core" etat={rejouer([refus()])} maintenant={T0} />).container;
    const deux = render(<Piece projet="ide-core" etat={rejouer([refus(), refus()])} maintenant={T0} />).container;

    expect(boules(un)).toBe(1);
    expect(boules(deux)).toBe(2);
  });

  it("draws three balls at most", () => {
    const etat = rejouer([refus(), refus(), refus(), refus(), refus()]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0} />);

    expect(boules(container)).toBe(3);
  });

  it("empties when the ticket events move on to the next ticket", () => {
    const { container, rerender } = render(
      <Piece projet="ide-core" etat={rejouer([refus(), refus()])} maintenant={T0} />,
    );
    expect(boules(container)).toBe(2);

    const suivant = rejouer([refus(), refus(), ev("queue_progress", null, {}, "ticket-002")]);
    rerender(<Piece projet="ide-core" etat={suivant} maintenant={T0} />);

    expect(boules(container)).toBe(0);
  });
});
