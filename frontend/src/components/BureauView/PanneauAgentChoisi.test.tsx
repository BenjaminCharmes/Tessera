import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import type { RunActif, UsageStats } from "../../types/api";
import { T0, etatEnCodage } from "./etatsDeTest";

const RUN: RunActif = {
  run_id: "run-1",
  project_id: "ide-core",
  mode: "ticket",
  ticket_id: "ticket-001",
  etape: null,
  agent: "codeur",
  tour: 1,
  tokens_entree: 0,
  tokens_sortie: 0,
  cout_usd: 0,
  verdict: null,
  demarre_a: "2026-10-23T09:59:00.000Z",
};

const CANAL = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };

function rendre(onOuvrir?: (runId: string) => void) {
  const projets: ProjetDuBureau[] = [{ nom: "ide-core", etat: etatEnCodage(), runId: "run-1", run: RUN }];
  return render(<BureauView projets={projets} {...CANAL} onOuvrir={onOuvrir} />);
}

function panneau(): HTMLElement {
  return screen.getByRole("complementary", { name: "Agent choisi" });
}

describe("PanneauAgentChoisi", () => {
  beforeEach(() => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.usage, "stats").mockResolvedValue({ daily: [] } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("invites to click an agent when none is chosen", () => {
    rendre();

    expect(within(panneau()).getByText("Clique un agent au travail")).toBeInTheDocument();
    expect(within(panneau()).queryByRole("button")).toBeNull();
  });

  it("shows role, project and ticket of the busy agent that was clicked", () => {
    rendre();

    fireEvent.click(screen.getByRole("button", { name: "Codeur, travaille" }));

    const dans = within(panneau());
    expect(dans.getByText("Codeur")).toBeInTheDocument();
    expect(dans.getByText("ide-core")).toBeInTheDocument();
    expect(dans.getByText("ticket-001")).toBeInTheDocument();
    expect(dans.queryByText("Clique un agent au travail")).toBeNull();
  });

  it("does not act on a free post and gives it no pointer cursor", () => {
    rendre();
    const libre = screen.getByRole("button", { name: "Reviewer, libre" });

    fireEvent.click(libre);

    expect(libre.className).not.toContain("cursor-pointer");
    expect(screen.getByRole("button", { name: "Codeur, travaille" }).className).toContain("cursor-pointer");
    expect(within(panneau()).getByText("Clique un agent au travail")).toBeInTheDocument();
  });

  it("opens the same thread as the room's Fil button", () => {
    const onOuvrir = vi.fn();
    rendre(onOuvrir);
    fireEvent.click(screen.getByRole("button", { name: "Codeur, travaille" }));

    fireEvent.click(within(panneau()).getByRole("button", { name: "Suivre le fil" }));

    expect(onOuvrir).toHaveBeenCalledTimes(1);
    expect(onOuvrir).toHaveBeenCalledWith("run-1");
    const piece = screen.getByRole("region", { name: "ide-core" });
    fireEvent.click(within(piece).getByRole("button", { name: "Ouvrir le fil de ticket-001" }));
    expect(onOuvrir).toHaveBeenLastCalledWith("run-1");
  });

  it("offers no thread without a way to open it", () => {
    rendre();
    fireEvent.click(screen.getByRole("button", { name: "Codeur, travaille" }));

    expect(within(panneau()).queryByRole("button")).toBeNull();
  });

  it("draws no model line, nor a write button", () => {
    rendre();
    fireEvent.click(screen.getByRole("button", { name: "Codeur, travaille" }));

    expect(within(panneau()).queryByText(/mod[eè]le/i)).toBeNull();
    expect(within(panneau()).queryByText(/écrire/i)).toBeNull();
  });
});
