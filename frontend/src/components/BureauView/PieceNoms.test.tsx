import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { api } from "../../lib/api";
import { nomDeLAgent } from "../../lib/bureau/noms";
import { apiQuota } from "../../lib/quota";
import type { UsageStats } from "../../types/api";
import BureauView from "./index";
import Piece from "./Piece";
import { T0, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Piece agent names", () => {
  it("opens the label of every desk with the name of its agent", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const postes = [
      ["codeur", "codeur, a fini"],
      ["testeur", "testeur, a fini"],
      ["securite", "sécurité, travaille"],
      ["reviewer", "reviewer, attend son tour"],
      ["validateur", "validateur, attend son tour"],
    ] as const;
    for (const [role, suite] of postes) {
      const attendu = `${nomDeLAgent("ide-core", role)}, ${suite}`;
      expect(screen.getByRole("button", { name: attendu })).toHaveAttribute("title", attendu);
    }
  });

  it("opens the label of a standing agent with its name", () => {
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const debout = container.querySelector('[data-agent="codeur"]');

    expect(debout?.getAttribute("aria-label")).toMatch(new RegExp(`^${nomDeLAgent("ide-core", "codeur")}, codeur, `));
  });

  it("gives the same agent the same name from one render to the next", () => {
    const premier = render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0} />);
    const lu = screen.getAllByRole("button").map((b) => b.getAttribute("aria-label"));
    premier.unmount();

    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0} />);

    expect(screen.getAllByRole("button").map((b) => b.getAttribute("aria-label"))).toEqual(lu);
  });
});

describe("PanneauAgentChoisi name", () => {
  beforeEach(() => {
    vi.spyOn(api.usage, "stats").mockResolvedValue({ daily: [] } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("titles the panel with the name of the chosen agent", () => {
    const canal = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };
    render(<BureauView projets={[{ nom: "ide-core", etat: etatEnCodage() }]} {...canal} />);
    const panneau = screen.getByRole("complementary", { name: "Agent choisi" });
    expect(within(panneau).getByRole("heading", { name: "Agent choisi" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: `${nomDeLAgent("ide-core", "codeur")}, codeur, travaille` }));

    expect(within(panneau).getByRole("heading", { name: nomDeLAgent("ide-core", "codeur") })).toBeInTheDocument();
  });
});
