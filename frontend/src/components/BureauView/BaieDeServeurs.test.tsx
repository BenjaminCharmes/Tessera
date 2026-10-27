import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BaieDeServeurs from "./BaieDeServeurs";
import BoutonServices from "../Sidebar/BoutonServices";
import { useServices } from "../../hooks/useServices";
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

/** Ce que fait la pièce : une lecture des services, la baie au mur et le bouton dans l'en-tête. */
function Harnais({ projet }: { projet: string }) {
  const services = useServices(projet, 0);
  return (
    <>
      <BaieDeServeurs services={services} />
      <BoutonServices services={services} libelleDuProjet={projet} />
    </>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("BaieDeServeurs", () => {
  it("is not rendered for a project without a declared service", async () => {
    const lire = vi.spyOn(api.services, "list").mockResolvedValue([]);

    const { container } = render(<Harnais projet="ide-core" />);

    await waitFor(() => expect(lire).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it("draws one rack level per declared service, with its state", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ nom: "api", en_cours: true }),
      service({ nom: "front", pid: 4243, code_de_sortie: 1 }),
    ]);

    const { container } = render(<Harnais projet="ide-core" />);

    const baie = await screen.findByRole("group", { name: "Services" });
    const voyants = [...container.querySelectorAll("[data-voyant]")].map((g) => g.getAttribute("data-voyant"));
    expect(voyants).toEqual(["en-cours", "echoue"]);
    // Les noms ne s'écrivent plus sous la baie : ils se lisent en infobulle.
    expect(screen.queryByText("api")).toBeNull();
    act(() => baie.focus());
    const lignes = within(screen.getByRole("tooltip")).getAllByRole("listitem");
    expect(lignes[0]?.textContent).toBe("api — en cours");
  });

  it("names each service and its state in the tooltip only", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service({ nom: "front", pid: null })]);

    render(<Harnais projet="ide-core" />);

    const baie = await screen.findByRole("group", { name: "Services" });
    expect(screen.queryByText(/pas lancé/)).toBeNull();
    act(() => baie.focus());
    expect(within(screen.getByRole("tooltip")).getByRole("listitem").textContent).toBe("front — pas lancé par l'IDE");
  });

  it("starts the services through the same endpoint as the services panel", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service()]);
    const lancer = vi.spyOn(api.services, "start").mockResolvedValue({ services: [] });

    render(<Harnais projet="ide-core" />);
    await userEvent.click(await screen.findByRole("button", { name: "Lancer les services de ide-core" }));

    expect(lancer).toHaveBeenCalledWith("ide-core");
  });

  it("stops the services through the same endpoint as the services panel", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service({ en_cours: true })]);
    const arreter = vi.spyOn(api.services, "stop").mockResolvedValue({ arretes: 1 });

    render(<Harnais projet="ide-core" />);
    await userEvent.click(await screen.findByRole("button", { name: "Arrêter les services de ide-core" }));

    expect(arreter).toHaveBeenCalledWith("ide-core");
  });
});
