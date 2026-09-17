import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentDetail from "./index";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const detail = vi.mocked(api.agents.detail);

describe("AgentDetail", () => {
  beforeEach(() => {
    detail.mockReset();
  });

  it("montre le prompt systeme en entier", async () => {
    // Panne d'usage : le prompt n'existait qu'en infobulle tronquee. Quand un
    // agent se comporte mal, c'est pourtant la premiere chose a lire — il
    // fallait ouvrir agents/prompts/*.md dans VSCode (ticket-076).
    detail.mockResolvedValue({
      role: "codeur",
      is_builtin: true,
      system_prompt: "Tu implémentes le ticket.\nTu ne commites jamais.",
    });

    render(<AgentDetail role="codeur" />);

    expect(await screen.findByText(/Tu ne commites jamais/)).toBeInTheDocument();
  });

  it("distingue un agent natif d'un agent cree", async () => {
    detail.mockResolvedValue({
      role: "mon-agent",
      is_builtin: false,
      system_prompt: "x",
    });

    render(<AgentDetail role="mon-agent" />);

    expect(await screen.findByText(/personnalisé/i)).toBeInTheDocument();
  });

  it("invite a choisir un agent quand aucun n'est selectionne", () => {
    render(<AgentDetail role={null} />);

    expect(screen.getByText(/Sélectionne un agent/i)).toBeInTheDocument();
    expect(detail).not.toHaveBeenCalled();
  });

  it("dit pourquoi le prompt manque plutot que de rester vide", async () => {
    detail.mockRejectedValue(new Error("404"));

    render(<AgentDetail role="fantome" />);

    expect(await screen.findByText(/Impossible de lire/i)).toBeInTheDocument();
  });
});

describe("AgentDetail — édition du prompt", () => {
  beforeEach(() => {
    detail.mockReset();
    vi.mocked(api.agents.updatePrompt).mockReset();
  });

  it("permet de modifier le prompt et de l'enregistrer", async () => {
    // Le prompt décide de tout ce que fait un agent. Le régler demandait
    // d'ouvrir le fichier dans VSCode juste après l'avoir lu à l'écran
    // (ticket-079).
    detail.mockResolvedValue({
      role: "codeur", is_builtin: true, system_prompt: "Tu implémentes.",
    });
    vi.mocked(api.agents.updatePrompt).mockResolvedValue({
      role: "codeur", is_builtin: true, system_prompt: "Tu testes d'abord.",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/Tu implémentes/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    const champ = screen.getByRole("textbox");
    await userEvent.clear(champ);
    await userEvent.type(champ, "Tu testes d'abord.");
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    expect(api.agents.updatePrompt).toHaveBeenCalledWith(
      "codeur",
      "Tu testes d'abord.",
    );
  });

  it("n'enregistre pas un prompt vide", async () => {
    detail.mockResolvedValue({
      role: "codeur", is_builtin: true, system_prompt: "Tu implémentes.",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/Tu implémentes/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    await userEvent.clear(screen.getByRole("textbox"));
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    expect(api.agents.updatePrompt).not.toHaveBeenCalled();
  });
});
