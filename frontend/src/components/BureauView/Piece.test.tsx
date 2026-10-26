import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { api } from "../../lib/api";
import Piece from "./Piece";
import { DERNIER, T0, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

function bulle(): string | null {
  return screen.queryByTestId("bulle")?.textContent ?? null;
}

function pastille(): string | null {
  const section = screen.getByRole("region", { name: "ide-core" });
  return section.querySelector("[data-etat]")?.textContent ?? null;
}

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

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

  it("draws a pill and no bubble for a busy post that works", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 5_000} />);

    expect(screen.queryByTestId("bulle")).toBeNull();
    expect(pastille()).toBe("travaille");
  });

  it("gives the post buttons no pointer cursor, as they have no click action", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    for (const bouton of screen.getAllByRole("button")) {
      expect(bouton.className).not.toContain("cursor-pointer");
    }
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
    { depuis: 5, question: null, mot: "travaille", signe: null },
    { depuis: 31, question: null, mot: "silencieux", signe: "…" },
    { depuis: 181, question: null, mot: "figé ?", signe: "!" },
    { depuis: 5, question: "On casse l'API ?", mot: "question", signe: "?" },
  ];

  it.each(cas)("shows $mot in the pill and $signe in the bubble at $depuis s", ({ depuis, question, mot, signe }) => {
    vi.setSystemTime(Date.parse(DERNIER) + depuis * 1000);
    render(
      <Piece
        projet="ide-core"
        etat={{ ...etatEnCodage(), pendingQuestion: question }}
        maintenant={Date.now()}
      />,
    );

    expect(bulle()).toBe(signe);
    expect(pastille()).toBe(mot);
    expect(screen.getByRole("button", { name: `Codeur, ${mot}` })).toBeInTheDocument();
  });
});
