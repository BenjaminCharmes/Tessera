import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PastilleSante from "./PastilleSante";

const MAINTENANT = new Date("2026-10-23T10:00:00.000Z");

function ilYa(secondes: number): string {
  return new Date(MAINTENANT.getTime() - secondes * 1000).toISOString();
}

describe("PastilleSante", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(MAINTENANT);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const cas = [
    { nom: "travaille", dernier: 5, question: null, libelle: "travaille", classe: "text-blue-300" },
    { nom: "silencieux", dernier: 60, question: null, libelle: "silencieux", classe: "text-zinc-300" },
    { nom: "question", dernier: 5, question: "On casse l'API ?", libelle: "question", classe: "text-amber-300" },
    { nom: "figé", dernier: 200, question: null, libelle: "figé ?", classe: "text-red-300" },
  ];

  it.each(cas)("renders $nom with its label and colour", ({ dernier, question, libelle, classe }) => {
    render(<PastilleSante dernierEvenementA={ilYa(dernier)} pendingQuestion={question} />);

    const pastille = screen.getByText(libelle);

    expect(pastille).toHaveClass(classe);
  });

  it("tells in the tooltip how long ago the last event was", () => {
    render(<PastilleSante dernierEvenementA={ilYa(60)} pendingQuestion={null} />);

    expect(screen.getByText("silencieux")).toHaveAttribute("title", "Dernier événement il y a 60 s");
  });

  it("says no event was received yet when the timestamp is missing", () => {
    render(<PastilleSante dernierEvenementA={null} pendingQuestion={null} />);

    expect(screen.getByText("travaille")).toHaveAttribute(
      "title",
      "Aucun événement reçu pour l'instant",
    );
  });
});
