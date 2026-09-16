import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NavRail from "./NavRail";
import type { SidebarPanel } from "./panels";

describe("NavRail", () => {
  it("affiche un libelle visible pour chaque destination", () => {
    // La barre precedente n'avait que des glyphes (des familles differentes :
    // geometrique, trigramme, horloge, engrenage, dollar) et une infobulle au
    // survol. On ne savait pas sur quoi on cliquait avant d'avoir clique.
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);

    for (const label of ["Projets", "Tickets", "Historique", "Agents", "Coûts"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("signale la destination courante aux lecteurs d'ecran", () => {
    render(<NavRail activePanel="history" onChangePanel={() => {}} />);

    const courant = screen.getByRole("tab", { name: /Historique/ });
    expect(courant).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Projets/ })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("remonte la destination choisie", async () => {
    const onChangePanel = vi.fn();
    render(<NavRail activePanel="projects" onChangePanel={onChangePanel} />);

    await userEvent.click(screen.getByRole("tab", { name: /Agents/ }));

    expect(onChangePanel).toHaveBeenCalledWith<[SidebarPanel]>("agents");
  });
});
