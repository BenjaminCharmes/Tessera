import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NavRail from "./NavRail";
import type { SidebarPanel } from "./panels";

describe("NavRail", () => {
  it("affiche le nom du produit dans la zone d'identite", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    expect(screen.getByText("Tessera")).toBeInTheDocument();
  });

  it("le nom du produit ne porte aucune classe text-violet-", () => {
    // ADR-026 : l'accent d'identité est une barre, jamais la couleur d'un mot.
    // Du violet sur du texte se lirait comme un état de plus.
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const nom = screen.getByText("Tessera");
    expect(nom.className).not.toMatch(/text-violet-/);
  });

  it("rend toujours les huit destinations sans regression", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(8);
  });

  it("propose une entree Chat", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    expect(screen.getByRole("tab", { name: /Chat/ })).toBeInTheDocument();
  });

  it("affiche un libelle visible pour chaque destination", () => {
    // La barre precedente n'avait que des glyphes (des familles differentes :
    // geometrique, trigramme, horloge, engrenage, dollar) et une infobulle au
    // survol. On ne savait pas sur quoi on cliquait avant d'avoir clique.
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);

    for (const label of [
      "Projets",
      "Tickets",
      "Historique",
      "Agents",
      "Supervision",
      "Statistiques",
      "Chat",
    ]) {
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

  it("n'affiche aucune pastille quand rien ne tourne", () => {
    // Un badge a zero occupe la place sans rien dire.
    render(
      <NavRail activePanel="projects" onChangePanel={() => {}} runsActifs={0} />,
    );
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("compte les runs, pas les agents", () => {
    // Un pipeline Tessera est sequentiel : il n'y a jamais deux agents
    // simultanes dans un meme run. Annoncer « 12 agents » serait faux.
    render(
      <NavRail activePanel="projects" onChangePanel={() => {}} runsActifs={3} />,
    );
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByLabelText("3 runs en cours")).toBeInTheDocument();
  });

  it("passe a l'ambre quand un agent attend une reponse", () => {
    render(
      <NavRail
        activePanel="projects"
        onChangePanel={() => {}}
        runsActifs={1}
        alerte="attente"
      />,
    );
    expect(screen.getByText("1").className).toMatch(/amber/);
  });

  it("passe au rouge quand un run est bloque", () => {
    render(
      <NavRail
        activePanel="projects"
        onChangePanel={() => {}}
        runsActifs={2}
        alerte="bloque"
      />,
    );
    expect(screen.getByText("2").className).toMatch(/red/);
  });

  it("reste dans le bleu de l'activite sans alerte", () => {
    // ADR-026 : cinq familles d'etat et elles seules.
    render(
      <NavRail activePanel="projects" onChangePanel={() => {}} runsActifs={1} />,
    );
    expect(screen.getByText("1").className).toMatch(/blue/);
  });
});
