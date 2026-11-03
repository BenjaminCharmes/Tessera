import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import { DUREE_DE_VISITE_MS } from "../../lib/bureau/ronde";
import { apiVentilation } from "../../lib/ventilation";
import { ventilation } from "../../test/contrat/exemples";
import type { OrchestratorEvent, UsageStats } from "../../types/api";
import { DERNIER, T0, etatEnCodage } from "./etatsDeTest";

const CANAL = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };

function enQuestion() {
  const evenements: OrchestratorEvent[] = [
    { type: "agent_started", agent: "codeur", ticket_id: "ticket-001", data: {}, timestamp: DERNIER },
    { type: "agent_question", agent: null, ticket_id: "ticket-001", data: { question: "Quelle option ?" }, timestamp: DERNIER },
  ];
  return evenements.reduce(applyEvent, INITIAL);
}

function salleDuDirecteur(): HTMLElement {
  return screen.getByRole("complementary", { name: "Bureau du directeur" });
}

function directeurEnVisite(projet: string): HTMLElement | null {
  return screen.getByRole("region", { name: projet }).querySelector('[data-directeur="visite"]');
}

function avancer(ms: number): void {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

describe("BureauView — the director's round", () => {
  beforeEach(() => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.runs, "list").mockResolvedValue([]);
    vi.spyOn(apiVentilation, "parProjet").mockResolvedValue(ventilation());
    vi.spyOn(api.usage, "stats").mockResolvedValue({ daily: [] } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("walks to the room of a run that goes silent, then back to his desk", () => {
    const projets: ProjetDuBureau[] = [{ nom: "projet-0", etat: etatEnCodage() }];
    render(<BureauView projets={projets} {...CANAL} />);
    expect(directeurEnVisite("projet-0")).toBeNull();
    expect(within(salleDuDirecteur()).getByRole("img", { name: "Ben, directeur" })).toBeInTheDocument();

    avancer(30_000);
    expect(directeurEnVisite("projet-0")?.getAttribute("data-poste")).toBe("codeur");
    // ticket-723 : son infobulle dit pourquoi il est venu.
    expect(directeurEnVisite("projet-0")?.getAttribute("aria-label")).toBe(
      "Ben, directeur, vient voir pourquoi le run se tait chez projet-0",
    );
    expect(within(salleDuDirecteur()).getByRole("img", { name: "Ben, directeur, en visite" })).toBeInTheDocument();

    avancer(DUREE_DE_VISITE_MS);
    expect(directeurEnVisite("projet-0")).toBeNull();
    expect(within(salleDuDirecteur()).getByRole("img", { name: "Ben, directeur" })).toBeInTheDocument();
  });

  it("comes for an agent the user clicks, even while the delay between visits runs", () => {
    render(<BureauView projets={[{ nom: "projet-0", etat: etatEnCodage() }]} {...CANAL} />);
    avancer(30_000);
    avancer(DUREE_DE_VISITE_MS);
    expect(directeurEnVisite("projet-0")).toBeNull();

    // La visite de santé date de 25 s : l'écart n'est pas écoulé, le clic passe quand même.
    fireEvent.click(within(screen.getByRole("region", { name: "projet-0" })).getByRole("button", { name: /codeur/i }));

    expect(directeurEnVisite("projet-0")).not.toBeNull();
  });

  it("keeps him at his desk while a question waits", () => {
    const projets: ProjetDuBureau[] = [
      { nom: "projet-0", etat: etatEnCodage() },
      { nom: "projet-1", etat: enQuestion() },
    ];
    render(<BureauView projets={projets} {...CANAL} />);

    avancer(60_000);

    expect(directeurEnVisite("projet-0")).toBeNull();
    expect(within(salleDuDirecteur()).getByRole("img", { name: "Ben, directeur" })).toBeInTheDocument();
  });

  it("still mounts a single interval while he visits", () => {
    render(<BureauView projets={[{ nom: "projet-0", etat: etatEnCodage() }]} {...CANAL} />);

    avancer(30_000);

    expect(directeurEnVisite("projet-0")).not.toBeNull();
    // L'image qui active la marche des agents passe d'abord : elle ne se répète pas (ticket-638).
    act(() => vi.advanceTimersToNextFrame());
    expect(vi.getTimerCount()).toBe(1);
  });
});
