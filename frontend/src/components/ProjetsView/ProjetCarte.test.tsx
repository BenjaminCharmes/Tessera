import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjetCarte from "./ProjetCarte";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    services: { start: vi.fn(), stop: vi.fn() },
  },
}));

const start = vi.mocked(api.services.start);
const stop = vi.mocked(api.services.stop);

function projet(extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id: "serpent",
    name: "Serpent",
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 0 },
    run_actif: false,
    icon: false,
    services_declares: true,
    services_en_cours: false,
    online_declared: false,
    ...extra,
  };
}

function afficher(p: ProjectOverview, onSelect = vi.fn(), onServicesChange = vi.fn()) {
  const rendu = render(
    <ProjetCarte
      projet={p}
      actif={false}
      categories={[]}
      onSelect={onSelect}
      onChangerCategorie={vi.fn()}
      onServicesChange={onServicesChange}
      onFileLancee={vi.fn()}
    />,
  );
  return { onSelect, onServicesChange, unmount: rendu.unmount };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProjetCarte services button", () => {
  it("starts the services without selecting the card, then asks for a reload", async () => {
    start.mockResolvedValue({ services: [] });
    const { onSelect, onServicesChange } = afficher(projet());

    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));

    expect(start).toHaveBeenCalledWith("serpent");
    expect(onSelect).not.toHaveBeenCalled();
    await waitFor(() => expect(onServicesChange).toHaveBeenCalledTimes(1));
  });

  it("offers to stop when the services are running", async () => {
    stop.mockResolvedValue({ arretes: 1 });
    const { onSelect } = afficher(projet({ services_en_cours: true }));

    expect(screen.queryByRole("button", { name: "Lancer" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Arrêter" }));

    expect(stop).toHaveBeenCalledWith("serpent");
    expect(start).not.toHaveBeenCalled();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("shows no button when the project declares no service", () => {
    afficher(projet({ services_declares: false }));

    expect(screen.queryByRole("button", { name: "Lancer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Arrêter" })).not.toBeInTheDocument();
  });

  it("shows the failure under the button and enables it again", async () => {
    start.mockRejectedValue(new Error("API 409: rien de déclaré"));
    const { onServicesChange } = afficher(projet());

    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("API 409: rien de déclaré");
    expect(screen.getByRole("button", { name: "Lancer" })).toBeEnabled();
    expect(onServicesChange).not.toHaveBeenCalled();
  });

  it("disables the button while the call is pending", async () => {
    let finir: (v: { services: [] }) => void = () => {};
    start.mockReturnValue(new Promise((resolve) => (finir = resolve)));
    afficher(projet());

    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));
    expect(screen.getByRole("button", { name: "Lancer" })).toBeDisabled();

    finir({ services: [] });
    await waitFor(() => expect(screen.getByRole("button", { name: "Lancer" })).toBeEnabled());
  });
});

describe("ProjetCarte services state", () => {
  it("marks the card of a project whose app is running", () => {
    afficher(projet({ services_declares: true, services_en_cours: true }));

    const carte = screen.getByRole("article");
    expect(carte.dataset.services).toBe("en-cours");
    expect(carte.className).toContain("border-blue-500/60");
  });

  it("marks a launchable project apart from one with nothing to launch", () => {
    const { unmount } = afficher(projet({ services_declares: true, services_en_cours: false }));
    expect(screen.getByRole("article").dataset.services).toBe("a-l-arret");
    unmount();

    afficher(projet({ services_declares: false }));
    expect(screen.getByRole("article").dataset.services).toBeUndefined();
  });
});

describe("ProjetCarte footer", () => {
  it("pins the dates and counters to the bottom, whatever the text above", () => {
    // Les cartes d'une rangée ont la même hauteur : sans pied poussé en bas,
    // « Créé… » et les compteurs flottaient à mi-hauteur sur une carte à la
    // description courte ou sans bouton Lancer.
    afficher(projet({ services_declares: false }));

    const pied = screen.getByTestId("pied-de-carte");
    expect(pied).toHaveClass("mt-auto");
    expect(pied).toHaveTextContent(/Créé/);
    expect(pied).toHaveTextContent(/À faire/);
  });

  it("keeps the counters row as tall with or without the Lancer button", () => {
    afficher(projet({ services_declares: false }));

    expect(screen.getByText(/À faire/).closest("ul")?.parentElement).toHaveClass("min-h-6");
  });
});
