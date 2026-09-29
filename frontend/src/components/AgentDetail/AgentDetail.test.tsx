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

  it("prévient qu'un prompt n'est jamais chargé", async () => {
    // Le cas qui manquait : quatre prompts sur dix-sept ne sont appelés par
    // rien. Les modifier ne change rien, et le badge le disait « requis ».
    detail.mockResolvedValue({
      role: "mon-agent",
      is_builtin: false,
      system_prompt: "x",
      moment: "jamais",
    });

    render(<AgentDetail role="mon-agent" />);

    expect(await screen.findByText("jamais appelé")).toBeInTheDocument();
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

    // Le diff est affiché — on confirme pour déclencher l'appel API.
    await userEvent.click(screen.getByRole("button", { name: /Confirmer/ }));

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

describe("AgentDetail — confirmation avant enregistrement (ticket-226)", () => {
  beforeEach(() => {
    detail.mockReset();
    vi.mocked(api.agents.updatePrompt).mockReset();
  });

  it("affiche les lignes retirées et ajoutées sans appeler l'API", async () => {
    detail.mockResolvedValue({
      role: "codeur",
      is_builtin: true,
      system_prompt: "ligne un\nligne deux",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/ligne un/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    const champ = screen.getByRole("textbox");
    await userEvent.clear(champ);
    await userEvent.type(champ, "ligne un\nligne trois");
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    // La ligne retirée et la ligne ajoutée sont visibles dans le diff.
    expect(screen.getByText("-ligne deux")).toBeInTheDocument();
    expect(screen.getByText("+ligne trois")).toBeInTheDocument();
    // L'API n'a pas encore été appelée.
    expect(api.agents.updatePrompt).not.toHaveBeenCalled();
  });

  it("appelle l'API après Confirmer", async () => {
    detail.mockResolvedValue({
      role: "codeur",
      is_builtin: true,
      system_prompt: "ancien prompt",
    });
    vi.mocked(api.agents.updatePrompt).mockResolvedValue({
      role: "codeur", is_builtin: true, system_prompt: "nouveau prompt",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/ancien prompt/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    const champ = screen.getByRole("textbox");
    await userEvent.clear(champ);
    await userEvent.type(champ, "nouveau prompt");
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));
    await userEvent.click(screen.getByRole("button", { name: /Confirmer/ }));

    expect(api.agents.updatePrompt).toHaveBeenCalledWith("codeur", "nouveau prompt");
  });

  it("garde le brouillon et n'appelle pas l'API après Annuler", async () => {
    detail.mockResolvedValue({
      role: "codeur",
      is_builtin: true,
      system_prompt: "ancien prompt",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/ancien prompt/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    const champ = screen.getByRole("textbox");
    await userEvent.clear(champ);
    await userEvent.type(champ, "brouillon en cours");
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    // Le diff est affiché — on annule.
    await userEvent.click(screen.getByRole("button", { name: /Annuler/ }));

    // Le brouillon est intact dans la textarea.
    expect(screen.getByRole("textbox")).toHaveValue("brouillon en cours");
    expect(api.agents.updatePrompt).not.toHaveBeenCalled();
  });

  it("n'ouvre pas le diff quand le brouillon est identique au prompt enregistré", async () => {
    detail.mockResolvedValue({
      role: "codeur",
      is_builtin: true,
      system_prompt: "prompt inchangé",
    });

    render(<AgentDetail role="codeur" />);
    await screen.findByText(/prompt inchangé/);

    await userEvent.click(screen.getByRole("tab", { name: "Modifier" }));
    // On ne modifie rien : le brouillon est identique au prompt enregistré.
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    // Aucun diff, aucun bouton Confirmer, aucun appel API.
    expect(screen.queryByRole("button", { name: /Confirmer/ })).toBeNull();
    expect(api.agents.updatePrompt).not.toHaveBeenCalled();
  });
});
