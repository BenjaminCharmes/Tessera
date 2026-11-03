import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BoutonMiseEnLigne from "./BoutonMiseEnLigne";
import ListeDesEtapes from "./ListeDesEtapes";
import { api } from "../../lib/api";
import { MockWebSocket } from "../../test/mockWebSocket";
import type { EtapeMiseEnLigne, EtatEtape, ProjectOverview } from "../../types/api";

vi.stubGlobal("WebSocket", MockWebSocket);

vi.mock("../../lib/api", () => ({
  api: { provisioning: { start: vi.fn(), read: vi.fn() } },
}));

const start = vi.mocked(api.provisioning.start);
const read = vi.mocked(api.provisioning.read);

function projet(extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id: "guessimo",
    name: "Guessimo",
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 0 },
    run_actif: false,
    icon: false,
    services_declares: false,
    services_en_cours: false,
    online_declared: true,
    online_domain: "guessimo.com",
    online_stripe_mode: "test",
    ...extra,
  };
}

function evenement(step: string, state: EtatEtape, detail = "") {
  MockWebSocket.instance?.triggerMessage({
    type: "provisioning_step",
    project_id: "guessimo",
    data: { step, state, detail },
  });
}

async function confirmer() {
  await userEvent.click(screen.getByRole("button", { name: "Mettre en ligne" }));
  const dialogue = screen.getByRole("dialog");
  await userEvent.click(within(dialogue).getByRole("button", { name: "Mettre en ligne" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  MockWebSocket.instance = null;
  read.mockResolvedValue([]);
});

describe("BoutonMiseEnLigne visibility", () => {
  it("shows the button only when the project declares an online block", () => {
    const { unmount } = render(<BoutonMiseEnLigne projet={projet()} />);
    expect(screen.getByRole("button", { name: "Mettre en ligne" })).toBeInTheDocument();
    unmount();

    render(<BoutonMiseEnLigne projet={projet({ online_declared: false })} />);
    expect(screen.queryByRole("button", { name: "Mettre en ligne" })).not.toBeInTheDocument();
  });
});

describe("BoutonMiseEnLigne confirmation", () => {
  it("names the domain and the Stripe mode, and calls nothing before confirming", async () => {
    render(<BoutonMiseEnLigne projet={projet()} />);

    await userEvent.click(screen.getByRole("button", { name: "Mettre en ligne" }));

    const dialogue = screen.getByRole("dialog");
    expect(within(dialogue).getByText("guessimo.com")).toBeInTheDocument();
    expect(within(dialogue).getByText("Stripe test")).toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
    expect(read).not.toHaveBeenCalled();
    expect(MockWebSocket.instance).toBeNull();
  });

  it("names the live mode when the project declares it", async () => {
    render(<BoutonMiseEnLigne projet={projet({ online_stripe_mode: "live" })} />);

    await userEvent.click(screen.getByRole("button", { name: "Mettre en ligne" }));

    expect(within(screen.getByRole("dialog")).getByText("Stripe live")).toBeInTheDocument();
  });

  it("calls nothing when the user cancels", async () => {
    render(<BoutonMiseEnLigne projet={projet()} />);
    await userEvent.click(screen.getByRole("button", { name: "Mettre en ligne" }));

    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
  });

  it("starts the provisioning once confirmed and shows the steps", async () => {
    start.mockResolvedValue({ project_id: "guessimo", steps: ["vercel_project", "dns"] });
    render(<BoutonMiseEnLigne projet={projet()} />);

    await confirmer();

    expect(start).toHaveBeenCalledWith("guessimo");
    const etapes = await screen.findByRole("list", { name: "Étapes de la mise en ligne" });
    expect(within(etapes).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("BoutonMiseEnLigne run", () => {
  it("disables the button while running and enables it when a step fails", async () => {
    start.mockResolvedValue({ project_id: "guessimo", steps: ["vercel_project", "dns"] });
    render(<BoutonMiseEnLigne projet={projet()} />);

    await confirmer();
    await screen.findByRole("dialog");
    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));

    const bouton = screen.getByRole("button", { name: "Mise en ligne…" });
    expect(bouton).toBeDisabled();

    act(() => evenement("vercel_project", "done", "Projet créé."));
    expect(screen.getByRole("button", { name: "Mise en ligne…" })).toBeDisabled();

    act(() => evenement("dns", "failed", "HTTP 403"));
    expect(screen.getByRole("button", { name: "Mettre en ligne" })).toBeEnabled();
  });

  it("updates each step from the events of this project only", async () => {
    start.mockResolvedValue({ project_id: "guessimo", steps: ["vercel_project", "database"] });
    render(<BoutonMiseEnLigne projet={projet()} />);
    await confirmer();
    await screen.findByRole("dialog");

    act(() => {
      evenement("vercel_project", "done", "Projet créé.");
      MockWebSocket.instance?.triggerMessage({
        type: "provisioning_step",
        project_id: "autre-projet",
        data: { step: "database", state: "failed", detail: "pas pour nous" },
      });
    });

    expect(screen.getByText("Projet créé.")).toBeInTheDocument();
    expect(screen.queryByText("pas pour nous")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Relancer" })).toBeDisabled();
  });

  it("lets an event win over a read that arrives after it", async () => {
    let rendreLecture: (etapes: EtapeMiseEnLigne[]) => void = () => undefined;
    read.mockReturnValue(new Promise((resolve) => (rendreLecture = resolve)));
    start.mockResolvedValue({ project_id: "guessimo", steps: ["vercel_project"] });
    render(<BoutonMiseEnLigne projet={projet()} />);
    await confirmer();
    await screen.findByRole("dialog");

    act(() => evenement("vercel_project", "done", "Créé."));
    await act(async () => {
      rendreLecture([{ step: "vercel_project", state: "todo", detail: "Manque." }]);
    });

    expect(screen.getByText("Créé.")).toBeInTheDocument();
    expect(screen.queryByText("Manque.")).not.toBeInTheDocument();
  });
});

describe("BoutonMiseEnLigne refusals", () => {
  it("shows a short message on a 409 and keeps the button enabled", async () => {
    start.mockRejectedValue(
      new Error('API 409: {"detail":"A provisioning is already running"}'),
    );
    render(<BoutonMiseEnLigne projet={projet()} />);

    await confirmer();

    const alerte = await screen.findByRole("alert");
    expect(alerte).toHaveTextContent("Une mise en ligne est déjà en cours pour ce projet.");
    expect(alerte).not.toHaveTextContent("API 409");
    expect(screen.getByRole("button", { name: "Mettre en ligne" })).toBeEnabled();
  });

  it("shows the reason of an invalid block and keeps the button enabled", async () => {
    start.mockRejectedValue(
      new Error('API 422: {"detail":"online.domain: must be a bare domain name"}'),
    );
    render(<BoutonMiseEnLigne projet={projet()} />);

    await confirmer();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "online.domain: must be a bare domain name",
    );
    expect(screen.getByRole("button", { name: "Mettre en ligne" })).toBeEnabled();
  });

  it("shows a generic message on any other failure", async () => {
    start.mockRejectedValue(new Error("Failed to fetch"));
    render(<BoutonMiseEnLigne projet={projet()} />);

    await confirmer();

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("La mise en ligne n'a pas pu démarrer."),
    );
    expect(screen.getByRole("button", { name: "Mettre en ligne" })).toBeEnabled();
  });
});

describe("ListeDesEtapes", () => {
  const ETATS: [EtatEtape, string, string][] = [
    ["todo", "à faire", "zinc"],
    ["done", "fait", "green"],
    ["skipped", "déjà là", "green"],
    ["pending", "en cours", "blue"],
    ["manual", "à faire à la main", "amber"],
    ["needs_human", "ton action requise", "amber"],
    ["failed", "échec", "red"],
  ];

  it.each(ETATS)("shows the %s state as « %s » in the %s family", (state, libelle, famille) => {
    render(<ListeDesEtapes etapes={[{ step: "dns", state, detail: "" }]} />);

    const pastille = screen.getByText(libelle);
    expect(pastille.className).toMatch(new RegExp(`text-${famille}-\\d`));
  });

  it("shows the detail of every step, manual and needs_human included", () => {
    render(
      <ListeDesEtapes
        etapes={[
          { step: "dns", state: "manual", detail: "Pose 5 enregistrements chez ton registrar." },
          { step: "stripe", state: "needs_human", detail: "Crée la clé restreinte." },
          { step: "database", state: "failed", detail: "HTTP 403 · permission_error" },
        ]}
      />,
    );

    expect(screen.getByText("Pose 5 enregistrements chez ton registrar.")).toBeInTheDocument();
    expect(screen.getByText("Crée la clé restreinte.")).toBeInTheDocument();
    expect(screen.getByText("HTTP 403 · permission_error").className).toMatch(/text-red-\d/);
  });
});
