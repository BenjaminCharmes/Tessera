import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnCoursView from "./index";
import { api } from "../../lib/api";
import { useAppsEnCours } from "../../hooks/useAppsEnCours";
import type { AppEnCours, ProjectOverview } from "../../types/api";

function app(over: Partial<AppEnCours>): AppEnCours {
  return {
    project_id: "alpha",
    project_name: "Alpha",
    nom: "api",
    origine: "tessera",
    pid: 100,
    ports: [8001],
    demarre_a: null,
    memoire_mo: 100,
    ...over,
  };
}

function projet(over: Partial<ProjectOverview>): ProjectOverview {
  return {
    id: "alpha",
    name: "Alpha",
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-01-01T00:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 0 },
    run_actif: false,
    icon: false,
    services_declares: true,
    services_en_cours: false,
    ...over,
  };
}

function Cockpit() {
  return <EnCoursView appsEnCours={useAppsEnCours()} />;
}

const GROUPE = [
  app({ pid: 1, nom: "front", memoire_mo: 200 }),
  app({ pid: 2, nom: "serveur", origine: "externe", memoire_mo: 100 }),
];

async function monter(apps: AppEnCours[], projets: ProjectOverview[] = []) {
  const lire = vi.spyOn(api.services, "running").mockResolvedValue(apps);
  vi.spyOn(api.projects, "overview").mockResolvedValue(projets);
  render(<Cockpit />);
  await act(async () => {});
  return lire;
}

function ligneDe(nom: string): HTMLElement {
  return screen.getByText(nom).closest("li") as HTMLElement;
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("Stopping a whole project", () => {
  it("stops the services then each external pid after a single confirmation", async () => {
    const arreterServices = vi.spyOn(api.services, "stop").mockResolvedValue({ arretes: 1 });
    const arreterPid = vi
      .spyOn(api.services, "stopRunning")
      .mockResolvedValue({ pid: 2, arretes: 1 });
    await monter(GROUPE);

    await userEvent.click(screen.getByRole("button", { name: "Arrêter le projet Alpha" }));
    expect(screen.getByText(/processus lancés à la main \(2\)/)).toBeInTheDocument();
    expect(arreterServices).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /Confirmer l.arrêt du projet/ }));

    expect(arreterServices).toHaveBeenCalledWith("alpha");
    expect(arreterPid).toHaveBeenCalledTimes(1);
    expect(arreterPid).toHaveBeenCalledWith(2);
  });

  it("stops a group made of Tessera services only, without asking", async () => {
    const arreterServices = vi.spyOn(api.services, "stop").mockResolvedValue({ arretes: 1 });
    const arreterPid = vi.spyOn(api.services, "stopRunning");
    await monter([app({ pid: 1 })]);

    await userEvent.click(screen.getByRole("button", { name: "Arrêter le projet Alpha" }));

    expect(arreterServices).toHaveBeenCalledWith("alpha");
    expect(arreterPid).not.toHaveBeenCalled();
  });
});

describe("Waiting for a stop", () => {
  it("disables the button and shows an indicator while the pid is still listed", async () => {
    vi.spyOn(api.services, "stopRunning").mockResolvedValue({ pid: 1, arretes: 1 });
    await monter([app({ pid: 1, nom: "front" })]);
    const ligne = ligneDe("front");

    await userEvent.click(within(ligne).getByRole("button", { name: "Arrêter front" }));
    await act(async () => {});

    expect(within(ligne).getByRole("button", { name: "Arrêter front" })).toBeDisabled();
    expect(within(ligne).getByText("Arrêt…")).toBeInTheDocument();
  });

  it("lifts the state once the pid left the inventory, reading every 2 s", async () => {
    vi.spyOn(api.services, "stopRunning").mockResolvedValue({ pid: 1, arretes: 1 });
    const lire = await monter([app({ pid: 1, nom: "front" }), app({ pid: 3, nom: "docs" })]);
    await userEvent.click(
      within(ligneDe("front")).getByRole("button", { name: "Arrêter front" }),
    );
    await act(async () => {});
    const avant = lire.mock.calls.length;

    lire.mockResolvedValue([app({ pid: 3, nom: "docs" })]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(lire.mock.calls.length).toBeGreaterThan(avant);
    expect(screen.queryByText("front")).not.toBeInTheDocument();
    expect(screen.queryByText("Arrêt…")).not.toBeInTheDocument();
  });

  it("gives up after 30 s: shows an error and re-enables the button", async () => {
    vi.spyOn(api.services, "stopRunning").mockResolvedValue({ pid: 1, arretes: 1 });
    await monter([app({ pid: 1, nom: "front" })]);
    const ligne = ligneDe("front");
    await userEvent.click(within(ligne).getByRole("button", { name: "Arrêter front" }));
    await act(async () => {});
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(31_000);
    });

    expect(screen.getByRole("alert")).toHaveTextContent(/Sans effet après 30 s/);
    expect(within(ligne).getByRole("button", { name: "Arrêter front" })).toBeEnabled();
    expect(within(ligne).queryByText("Arrêt…")).not.toBeInTheDocument();
  });
});

describe("Stopped projects", () => {
  it("lists a project that declares services and has no app left, with a launch button", async () => {
    await monter(
      [app({ pid: 1 })],
      [
        projet({ id: "alpha", name: "Alpha" }),
        projet({ id: "beta", name: "Beta" }),
        projet({ id: "gamma", name: "Gamma", services_declares: false }),
      ],
    );

    const section = await screen.findByRole("region", { name: "Arrêtés" });
    expect(within(section).getByText("Beta")).toBeInTheDocument();
    expect(within(section).getByRole("button", { name: "Lancer Beta" })).toBeInTheDocument();
    expect(within(section).queryByText("Alpha")).not.toBeInTheDocument();
    expect(within(section).queryByText("Gamma")).not.toBeInTheDocument();
  });

  it("starts the project and shows a pending state until it is back in the inventory", async () => {
    const demarrer = vi.spyOn(api.services, "start").mockResolvedValue({ services: [] });
    const lire = await monter([], [projet({ id: "beta", name: "Beta" })]);
    const section = await screen.findByRole("region", { name: "Arrêtés" });

    await userEvent.click(within(section).getByRole("button", { name: "Lancer Beta" }));
    await act(async () => {});

    expect(demarrer).toHaveBeenCalledWith("beta");
    expect(within(section).getByRole("button", { name: "Lancer Beta" })).toBeDisabled();
    expect(within(section).getByText("Lancement…")).toBeInTheDocument();

    lire.mockResolvedValue([app({ project_id: "beta", project_name: "Beta", pid: 9 })]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(screen.queryByText("Lancement…")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Arrêtés" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Beta" })).toBeInTheDocument();
  });

  it("starts collapsed above five projects and opens on click", async () => {
    const sept = Array.from({ length: 7 }, (_, i) => projet({ id: `p${i}`, name: `Projet ${i}` }));
    await monter([], sept);

    const section = await screen.findByRole("region", { name: "Arrêtés" });
    expect(within(section).queryByRole("button", { name: /Lancer/ })).not.toBeInTheDocument();

    await userEvent.click(within(section).getByRole("button", { name: /Arrêtés \(7\)/ }));
    expect(within(section).getAllByRole("button", { name: /Lancer/ })).toHaveLength(7);
  });
});
