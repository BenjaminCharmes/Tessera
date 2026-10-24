import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import Piece from "./Piece";
import { DERNIER, T0, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

function bulle(): string | null {
  return screen.getByTestId("bulle").textContent;
}

function pastille(): string | null {
  const section = screen.getByRole("region", { name: "ide-core" });
  return section.querySelector("[data-etat]")?.textContent ?? null;
}

describe("Piece", () => {
  it("renders five posts, one button each, named with their state", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const boutons = screen.getAllByRole("button");
    expect(boutons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Codeur, fait",
      "Testeur, fait",
      "Sécurité, travaille",
      "Reviewer, libre",
      "Validateur, libre",
    ]);
  });

  it("names a busy, a done and a free post", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    expect(screen.getByRole("button", { name: "Sécurité, travaille" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Codeur, fait" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reviewer, libre" })).toBeInTheDocument();
  });

  it("draws a bubble and a pill only for the busy post", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 5_000} />);

    expect(screen.getAllByTestId("bulle")).toHaveLength(1);
    expect(pastille()).toBe("travaille");
  });

  it("draws neither bubble nor pill when no post is busy", () => {
    const etat = { ...etatEnCodage(), runClosed: true };
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} />);

    expect(screen.queryByTestId("bulle")).toBeNull();
    expect(within(screen.getByRole("region")).queryByText("travaille")).toBeNull();
  });

  it("outlines the room in amber when a question waits", () => {
    const etat = { ...etatEnCodage(), pendingQuestion: "On casse l'API ?" };
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} />);

    expect(screen.getByRole("region")).toHaveAttribute("data-contour", "amber");
  });
});

describe("Piece health words", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const cas = [
    { depuis: 5, question: null, mot: "travaille" },
    { depuis: 31, question: null, mot: "silencieux" },
    { depuis: 181, question: null, mot: "figé ?" },
    { depuis: 5, question: "On casse l'API ?", mot: "question" },
  ];

  it.each(cas)("shows $mot in the bubble and the pill at $depuis s", ({ depuis, question, mot }) => {
    vi.setSystemTime(Date.parse(DERNIER) + depuis * 1000);
    render(
      <Piece
        projet="ide-core"
        etat={{ ...etatEnCodage(), pendingQuestion: question }}
        maintenant={Date.now()}
      />,
    );

    expect(bulle()).toBe(mot);
    expect(pastille()).toBe(mot);
    expect(screen.getByRole("button", { name: `Codeur, ${mot}` })).toBeInTheDocument();
  });
});
