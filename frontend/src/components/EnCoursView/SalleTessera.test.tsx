import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnCoursView from "./index";
import { api } from "../../lib/api";
import { lireActivite } from "../../lib/apiActivite";
import { lireLaSalleTessera } from "../../lib/apiSalleTessera";
import { apiQuota } from "../../lib/quota";
import { _viderCacheResource } from "../../hooks/useResource";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import type { SalleTessera } from "../../types/salleTessera";

vi.mock("../../lib/apiActivite", () => ({ lireActivite: vi.fn() }));
vi.mock("../../lib/apiSalleTessera", () => ({ lireLaSalleTessera: vi.fn() }));

function salle(over: Partial<SalleTessera> = {}): SalleTessera {
  return {
    processus: [
      { nom: "backend", port: 8100, pid: 2788, memoire_mo: 148.1, demarre_a: "2026-10-30T12:26:18Z" },
      { nom: "frontend", port: 5173, pid: 3010, memoire_mo: 136.6, demarre_a: null },
    ],
    ollama: { url: "http://127.0.0.1:11434", refroidissement_s: null },
    runs: [
      { project_id: "ide-core", ticket_id: "ticket-677", agent: "codeur", etape: "production", file_index: 4, file_total: 38, suivants: ["ticket-708", "ticket-713"] },
    ],
    ci_en_attente: { curio: ["ticket-070"] },
    journal: [
      { ts: "2026-10-30T14:17:09Z", niveau: "INFO", evenement: "pull_request_opened", ticket_id: "ticket-718", role: null },
      { ts: "2026-10-30T14:17:10Z", niveau: "ERROR", evenement: "livraison_echouee", ticket_id: null, role: null },
    ],
    base_mo: 122,
    worktrees: 2,
    ...over,
  };
}

function rendre(vueInitiale: "salles" | "liste" = "salles") {
  const etat: UseAppsEnCoursResult = {
    apps: [], lueA: Date.parse("2026-10-30T14:20:00Z"), erreur: null,
    arreter: vi.fn(), rafraichir: vi.fn(), arreterProjet: vi.fn(), lancer: vi.fn(),
    enArret: () => false, enLancement: () => false,
  };
  return render(<EnCoursView appsEnCours={etat} vueInitiale={vueInitiale} />);
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.projects, "overview").mockResolvedValue([]);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.mocked(lireActivite).mockResolvedValue([]);
  vi.spyOn(apiQuota, "fenetres").mockResolvedValue({
    windows: { seven_day: { status: "allowed_warning", utilization: 0.88, resets_at: "2026-10-31T13:00:00Z", observed_at: "2026-10-30T14:00:00Z" } },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the Tessera server room (ticket-726)", () => {
  it("stands first, even when no project app runs, and has no stop button", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle());
    rendre();

    const piece = await screen.findByRole("article", { name: "Salle Tessera" });
    expect(screen.getByText("Aucune app de projet ne tourne")).toBeInTheDocument();
    expect(within(piece).getByText("fait tourner l'IDE")).toBeInTheDocument();
    expect(within(piece).queryByRole("button", { name: /Arrêter/ })).toBeNull();
  });

  it("shows the live queue, the PRs the CIWatcher waits on, and the log", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle());
    rendre();

    const runs = await screen.findByText("ide-core · ticket-677 · codeur");
    const ecranRuns = runs.closest("[data-ecran-tessera]") as HTMLElement;
    expect(within(ecranRuns).getByText("file 4 / 38")).toBeInTheDocument();
    expect(within(ecranRuns).getByText("puis ticket-708")).toBeInTheDocument();
    expect(screen.getByText("curio · ticket-070 · CI ou merge")).toBeInTheDocument();
    expect(screen.getByText(/livraison_echouee/)).toHaveClass("text-red-300");
  });

  it("draws one rack per Tessera server and turns the GPU rack amber while Ollama cools down", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle({ ollama: { url: "http://127.0.0.1:11434", refroidissement_s: 42 } }));
    rendre();

    await screen.findByRole("article", { name: "Salle Tessera" });
    expect(document.querySelectorAll("[data-salle-tessera] [data-sprite='baie-haute']")).toHaveLength(2);
    expect(document.querySelector("[data-sprite='baie-gpu']")).toHaveAttribute("data-etat", "refroidissement");
    expect(screen.getByRole("group", { name: "Ollama : en refroidissement" })).toBeInTheDocument();
  });

  it("reads the weekly quota, the database size and the open worktrees", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle());
    rendre();

    expect(await screen.findByText(/88 % · remis à zéro/)).toBeInTheDocument();
    expect(screen.getByText("tessera.db 122,0 Mo")).toBeInTheDocument();
    expect(screen.getByText("2 worktrees ouverts")).toBeInTheDocument();
  });

  it("says so on a screen that has nothing to show", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle({ runs: [], ci_en_attente: {}, journal: [] }));
    rendre();

    expect(await screen.findByText("(aucun run)")).toBeInTheDocument();
    expect(screen.getByText("(aucune PR en attente)")).toBeInTheDocument();
    expect(screen.getByText("(journal vide)")).toBeInTheDocument();
  });

  it("is left out of the list view", async () => {
    vi.mocked(lireLaSalleTessera).mockResolvedValue(salle());
    rendre("liste");
    await userEvent.click(screen.getByRole("button", { name: "Liste" }));

    expect(screen.queryByRole("article", { name: "Salle Tessera" })).toBeNull();
  });
});
