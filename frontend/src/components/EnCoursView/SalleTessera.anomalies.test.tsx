import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import EnCoursView from "./index";
import { api } from "../../lib/api";
import { lireActivite } from "../../lib/apiActivite";
import { lireLaSalleTessera } from "../../lib/apiSalleTessera";
import { apiQuota } from "../../lib/quota";
import { _viderCacheResource } from "../../hooks/useResource";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import type { RunVivant, SalleTessera } from "../../types/salleTessera";
import { lignesDesRuns } from "./lignesDeTessera";

vi.mock("../../lib/apiActivite", () => ({ lireActivite: vi.fn() }));
vi.mock("../../lib/apiSalleTessera", () => ({ lireLaSalleTessera: vi.fn() }));

function run(anomalies: number): RunVivant {
  return {
    project_id: "ide-core", ticket_id: "ticket-677", agent: "codeur", etape: "production",
    file_index: 0, file_total: 0, suivants: [], anomalies,
  };
}

function salle(anomalies: number): SalleTessera {
  return {
    processus: [{ nom: "backend", port: 8100, pid: 1, memoire_mo: 100, demarre_a: null }],
    ollama: { url: "http://127.0.0.1:11434", refroidissement_s: null },
    runs: [run(anomalies)],
    ci_en_attente: {},
    journal: [],
    base_mo: 10,
    agents: 1,
    runs_du_jour: 1,
  };
}

function rendre() {
  const etat: UseAppsEnCoursResult = {
    apps: [], lueA: Date.parse("2026-11-05T12:00:00Z"), erreur: null,
    arreter: vi.fn(), rafraichir: vi.fn(), arreterProjet: vi.fn(), lancer: vi.fn(),
    enArret: () => false, enLancement: () => false,
  };
  return render(<EnCoursView appsEnCours={etat} vueInitiale="salles" />);
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.projects, "overview").mockResolvedValue([]);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.usage, "recentRuns").mockResolvedValue([]);
  vi.mocked(lireActivite).mockResolvedValue([]);
  vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the Tessera room counts the anomalies of each live run (ticket-833)", () => {
  it("test_salle_tessera_run_row_shows_nothing_for_zero_anomalies", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle(0));
    rendre();

    await screen.findByText("ide-core · ticket-677 · codeur");
    expect(screen.queryByText(/anomalie/)).toBeNull();
    expect(lignesDesRuns(salle(0)).map((l) => l.texte)).toEqual(["ide-core · ticket-677 · codeur"]);
  });

  it("test_salle_tessera_run_row_says_1_anomaly_in_the_singular", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle(1));
    rendre();

    expect(await screen.findByText("1 anomalie")).toBeInTheDocument();
  });

  it("test_salle_tessera_run_row_says_2_anomalies_in_the_plural", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle(2));
    rendre();

    expect(await screen.findByText("2 anomalies")).toBeInTheDocument();
  });

  it("test_salle_tessera_anomaly_count_uses_amber_never_violet_text", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle(2));
    rendre();

    const ligne = await screen.findByText("2 anomalies");
    expect(ligne.className).toContain("text-amber-300");
    expect(ligne.className).not.toMatch(/text-violet/);
    const ligneDuRun = lignesDesRuns(salle(2)).find((l) => l.texte === "2 anomalies");
    expect(ligneDuRun?.ton).toBe("text-amber-300");
  });
});
