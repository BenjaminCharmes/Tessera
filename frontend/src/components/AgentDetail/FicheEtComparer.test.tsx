import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentDetail from "./index";
import { chiffresDuRole, phraseDuRole } from "./chiffres";
import type {
  BreakdownLine,
  ProjectAgentConfig,
  ProjectAgents,
  UsageStats,
} from "../../types/api";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

function ligne(key: string, calls: number, cost_usd: number): BreakdownLine {
  return { key, calls, cost_usd, tokens: 1000, avg_duration_ms: 500 };
}

function stats(perAgent: BreakdownLine[]): UsageStats {
  return {
    days: 30,
    project_id: "p",
    since: "2026-09-14",
    until: "2026-10-14",
    totals: {
      runs: 0,
      calls: 0,
      input_tokens: 0,
      output_tokens: 0,
      cache_read_tokens: 0,
      pipeline_cost_usd: 0,
      chat_cost_usd: 0,
      cost_usd: 0,
      call_duration_ms: 0,
    },
    daily: [],
    per_agent: perAgent,
    per_model: [],
    per_project: [],
    quality: {
      finished_runs: 0,
      approval_rate: null,
      avg_rounds: null,
      avg_run_duration_ms: null,
      by_status: [],
    },
    recent_runs: [],
  };
}

function config(role: string, model: string, active = true): ProjectAgentConfig {
  return {
    role,
    model,
    max_tokens: 8192,
    active,
    provider: "agent_sdk",
    fallback: null,
  };
}

const PROJET: ProjectAgents = {
  agents: [
    config("codeur", "claude-sonnet-5-5"),
    config("reviewer", "claude-opus-5-5"),
    config("testeur", "claude-haiku-4-5", false),
  ],
  known_models: ["claude-sonnet-5-5", "claude-opus-5-5"],
  known_providers: ["agent_sdk"],
  known_models_by_provider: { agent_sdk: ["claude-sonnet-5-5", "claude-opus-5-5"] },
};

const PER_AGENT = [ligne("reviewer", 17, 3.4182)];

beforeEach(() => {
  vi.mocked(api.agents.list).mockReset().mockResolvedValue([]);
  vi.mocked(api.agents.detail)
    .mockReset()
    .mockImplementation((role) =>
      Promise.resolve({
        role,
        is_builtin: true,
        system_prompt: `# ${role}\nTu relis le diff de ${role}.`,
      }),
    );
  vi.mocked(api.git.agents).mockReset().mockResolvedValue(PROJET);
  vi.mocked(api.usage.stats).mockReset().mockResolvedValue(stats(PER_AGENT));
  vi.mocked(api.runs.list).mockReset().mockResolvedValue([]);
});

describe("Fiche d'un rôle", () => {
  it("affiche les appels et le coût du rôle tirés de per_agent", async () => {
    render(<AgentDetail role="reviewer" projectId="p" />);

    expect(await screen.findByText("17")).toBeInTheDocument();
    expect(screen.getByText("$3.42")).toBeInTheDocument();
    expect(api.usage.stats).toHaveBeenCalledWith(30, "p");
  });

  it("affiche « — » pour un rôle absent de per_agent, jamais 0 $", async () => {
    render(<AgentDetail role="codeur" projectId="p" />);

    await waitFor(() => expect(screen.getAllByText("—")).toHaveLength(2));
    expect(screen.queryByText(/\$0/)).toBeNull();
  });

  it("résume le rôle par la première ligne de texte de son prompt", async () => {
    render(<AgentDetail role="codeur" projectId="p" />);

    // Le titre Markdown n'est pas une phrase : la ligne qui suit l'est.
    expect(await screen.findAllByText("Tu relis le diff de codeur.")).not.toHaveLength(0);
  });

  it("liste les derniers verdicts d'un rôle qui juge", async () => {
    vi.mocked(api.runs.list).mockResolvedValue([
      {
        id: "r1",
        ticket_id: "ticket-424",
        started_at: "2026-10-13T10:00:00Z",
        finished_at: "2026-10-13T10:20:00Z",
        rounds: 2,
        approved: true,
        final_status: "approved",
        total_cost_usd: 1,
      },
    ]);

    render(<AgentDetail role="reviewer" projectId="p" />);

    expect(await screen.findByText("ticket-424")).toBeInTheDocument();
    expect(screen.getByText("Approuvé après 2 tours")).toBeInTheDocument();
  });

  it("ne montre pas de verdicts pour un rôle qui ne juge pas", async () => {
    render(<AgentDetail role="codeur" projectId="p" />);
    await screen.findAllByText("Tu relis le diff de codeur.");

    expect(screen.queryByText("Derniers verdicts")).toBeNull();
    expect(api.runs.list).not.toHaveBeenCalled();
  });
});

describe("Comparer les rôles", () => {
  async function ouvrirComparer() {
    await userEvent.click(screen.getByRole("button", { name: "Comparer" }));
  }

  it("bascule vers « Comparer » et montre une ligne par rôle actif avec son modèle", async () => {
    render(<AgentDetail role="reviewer" projectId="p" />);
    await ouvrirComparer();

    const reviewer = await screen.findByRole("button", { name: /^reviewer.*claude-opus-5-5/ });
    const codeur = screen.getByRole("button", { name: /^codeur.*claude-sonnet-5-5/ });
    // Un rôle désactivé sur ce projet n'a pas de ligne.
    expect(screen.queryByRole("button", { name: /^testeur/ })).toBeNull();
    await waitFor(() => expect(within(reviewer).getByText("17")).toBeInTheDocument());
    expect(within(reviewer).getByText("$3.42")).toBeInTheDocument();
    expect(within(codeur).getAllByText("—")).toHaveLength(2);
  });

  it("ouvre la fiche du rôle au clic sur sa ligne", async () => {
    function Cockpit() {
      const [role, setRole] = useState<string | null>("codeur");
      return <AgentDetail role={role} projectId="p" onSelectRole={setRole} />;
    }
    render(<Cockpit />);
    await ouvrirComparer();

    await userEvent.click(await screen.findByRole("button", { name: /^reviewer/ }));

    expect(await screen.findAllByText("Tu relis le diff de reviewer.")).not.toHaveLength(0);
    expect(api.agents.detail).toHaveBeenCalledWith("reviewer");
    expect(screen.getByRole("button", { name: "Fiche" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("invite à ouvrir un projet quand il n'y en a pas", async () => {
    render(<AgentDetail role={null} projectId={null} />);
    await ouvrirComparer();

    expect(screen.getByText(/Ouvre un projet pour comparer/)).toBeInTheDocument();
    expect(api.git.agents).not.toHaveBeenCalled();
  });
});

describe("chiffres.ts", () => {
  it("chiffresDuRole rend « — » sans ligne ou sans appel", () => {
    const lignes = [ligne("reviewer", 3, 1.5), ligne("codeur", 0, 0)];

    expect(chiffresDuRole(lignes, "reviewer")).toEqual({ appels: "3", cout: "$1.50" });
    expect(chiffresDuRole(lignes, "codeur")).toEqual({ appels: "—", cout: "—" });
    expect(chiffresDuRole(lignes, "inconnu")).toEqual({ appels: "—", cout: "—" });
  });

  it("phraseDuRole préfère la description, sinon la première ligne non titre", () => {
    expect(phraseDuRole("Relit le diff.", "# Titre\nTexte")).toBe("Relit le diff.");
    expect(phraseDuRole("  ", "# Titre\n\nTexte du prompt\nSuite")).toBe("Texte du prompt");
    expect(phraseDuRole(null, "# Seulement un titre")).toBe("");
  });
});
