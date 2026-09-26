import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ModelPicker from "./ModelPicker";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const agents = vi.mocked(api.git.agents);
const setModel = vi.mocked(api.git.setAgentModel);

const GRILLE = ["claude-haiku-4-5", "claude-sonnet-4-6"];

const REPONSE = {
  agents: [
    {
      role: "codeur",
      model: "claude-sonnet-4-6",
      max_tokens: 8192,
      active: true,
      provider: "agent_sdk",
      fallback: null,
    },
  ],
  known_models: GRILLE,
  known_providers: ["agent_sdk", "anthropic_api", "local"],
  known_models_by_provider: {
    agent_sdk: GRILLE,
    anthropic_api: GRILLE,
    local: [],
  },
};

describe("ModelPicker", () => {
  beforeEach(() => {
    agents.mockReset();
    setModel.mockReset();
  });

  it("montre le modele utilise par cet agent sur ce projet", async () => {
    agents.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);

    expect(await screen.findByLabelText("Modèle sur ce projet")).toHaveValue(
      "claude-sonnet-4-6",
    );
  });

  it("n'offre que des modeles que l'app sait tarifer sur un provider Anthropic", async () => {
    // Choisir hors grille fausserait la ventilation des couts, qui est
    // justement ce sur quoi on s'appuie pour descendre en gamme (ticket-080).
    agents.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    const select = await screen.findByLabelText("Modèle sur ce projet");

    expect(
      Array.from((select as HTMLSelectElement).options).map((o) => o.textContent),
    ).toEqual(GRILLE);
  });

  it("enregistre le changement de modele", async () => {
    agents.mockResolvedValue(REPONSE);
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Modèle sur ce projet"),
      "claude-haiku-4-5",
    );

    expect(setModel).toHaveBeenCalledWith("p", "codeur", {
      model: "claude-haiku-4-5",
    });
  });

  it("enregistre le changement de provider", async () => {
    // ticket-188 : le provider se declare par role. Le modele courant est
    // dans la grille du nouveau provider, il est garde.
    agents.mockResolvedValue(REPONSE);
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Provider sur ce projet"),
      "anthropic_api",
    );

    expect(setModel).toHaveBeenCalledWith("p", "codeur", {
      model: "claude-sonnet-4-6",
      provider: "anthropic_api",
    });
  });

  it("laisse le nom du modele libre quand le provider n'a pas de grille", async () => {
    agents.mockResolvedValue({
      ...REPONSE,
      agents: [{ ...REPONSE.agents[0], provider: "local", model: "qwen" }],
    });
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    const champ = await screen.findByLabelText("Modèle sur ce projet");
    expect(champ.tagName).toBe("INPUT");

    await userEvent.clear(champ);
    await userEvent.type(champ, "qwen3-coder:30b");
    await userEvent.tab();

    expect(setModel).toHaveBeenCalledWith("p", "codeur", { model: "qwen3-coder:30b" });
  });

  it("active un repli sur le premier provider connu", async () => {
    agents.mockResolvedValue(REPONSE);
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    await userEvent.click(await screen.findByLabelText("Repli si indisponible"));

    expect(setModel).toHaveBeenCalledWith("p", "codeur", {
      model: "claude-sonnet-4-6",
      fallback: { provider: "agent_sdk", model: "claude-haiku-4-5" },
    });
  });

  it("retire le repli avec fallback a null, pas en l'omettant", async () => {
    // Omis, le backend garde le repli ; seul `null` le retire.
    const avecRepli = {
      ...REPONSE,
      agents: [
        {
          ...REPONSE.agents[0],
          fallback: { provider: "agent_sdk", model: "claude-haiku-4-5" },
        },
      ],
    };
    agents.mockResolvedValue(avecRepli);
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    expect(await screen.findByLabelText("Modèle de repli")).toHaveValue(
      "claude-haiku-4-5",
    );
    await userEvent.click(screen.getByLabelText("Repli si indisponible"));

    expect(setModel).toHaveBeenCalledWith("p", "codeur", {
      model: "claude-sonnet-4-6",
      fallback: null,
    });
  });

  it("se tait quand le projet ne declare pas cet agent", async () => {
    agents.mockResolvedValue({ ...REPONSE, agents: [] });

    const { container } = render(<ModelPicker projectId="p" role="codeur" />);

    await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
