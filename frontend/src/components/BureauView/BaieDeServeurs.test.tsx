import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BaieDeServeurs from "./BaieDeServeurs";
import { api } from "../../lib/api";
import type { ServiceActif } from "../../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "api",
    project_id: "ide-core",
    pid: 4242,
    demarre_a: "2026-10-24T10:00:00Z",
    en_cours: false,
    code_de_sortie: null,
    ...over,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("BaieDeServeurs", () => {
  it("is not rendered for a project without a declared service", async () => {
    const lire = vi.spyOn(api.services, "list").mockResolvedValue([]);

    const { container } = render(<BaieDeServeurs projet="ide-core" signalServices={0} />);

    await waitFor(() => expect(lire).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it("draws one rack level per declared service, with its state", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ nom: "api", en_cours: true }),
      service({ nom: "front", pid: 4243, code_de_sortie: 1 }),
    ]);

    const { container } = render(<BaieDeServeurs projet="ide-core" signalServices={0} />);

    expect(await screen.findByRole("group", { name: "Services" })).toBeInTheDocument();
    const voyants = [...container.querySelectorAll("[data-voyant]")].map((g) => g.getAttribute("data-voyant"));
    expect(voyants).toEqual(["en-cours", "echoue"]);
    expect(screen.getByText("api").closest("li")).toHaveAttribute("title", "en cours");
    expect(screen.queryByText(/en cours/)).toBeNull();
  });

  it("puts the state of a service in a title, not in the text under it", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service({ nom: "front", pid: null })]);

    render(<BaieDeServeurs projet="ide-core" signalServices={0} />);

    const ligne = (await screen.findByText("front")).closest("li");
    expect(ligne).toHaveAttribute("title", "pas lancé par l'IDE");
    expect(ligne?.textContent).toBe("front");
    expect(screen.queryByText(/pas lancé/)).toBeNull();
  });

  it("starts the services through the same endpoint as the services panel", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service()]);
    const lancer = vi.spyOn(api.services, "start").mockResolvedValue({ services: [] });

    render(<BaieDeServeurs projet="ide-core" signalServices={0} />);
    await userEvent.click(await screen.findByRole("button", { name: "Lancer les services de ide-core" }));

    expect(lancer).toHaveBeenCalledWith("ide-core");
  });

  it("stops the services through the same endpoint as the services panel", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service({ en_cours: true })]);
    const arreter = vi.spyOn(api.services, "stop").mockResolvedValue({ arretes: 1 });

    render(<BaieDeServeurs projet="ide-core" signalServices={0} />);
    await userEvent.click(await screen.findByRole("button", { name: "Arrêter les services de ide-core" }));

    expect(arreter).toHaveBeenCalledWith("ide-core");
  });
});
