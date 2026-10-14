import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import NavRail from "./NavRail";
import type { ReglageDesNotifications } from "./ReglageNotifications";
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

  it("rend les neuf destinations sans regression", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(9);
  });

  it("place En cours juste apres Projets", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const noms = screen.getAllByRole("tab").map((t) => t.textContent);
    expect(noms[0]).toMatch(/Projets/);
    expect(noms[1]).toMatch(/En cours/);
  });

  it("ordonne les neuf destinations par groupe", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const noms = screen.getAllByRole("tab").map((t) => t.textContent ?? "");
    const attendu = [
      "Projets",
      "En cours",
      "Supervision",
      "Tickets",
      "Fichiers",
      "Historique",
      "Agents",
      "Statistiques",
      "Chat",
    ];
    expect(noms).toHaveLength(attendu.length);
    attendu.forEach((nom, i) => expect(noms[i]).toMatch(nom));
  });

  it("place chaque intitule avant les destinations de son groupe", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const ordre = (a: Node, b: Node): boolean =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    const groupes: Array<[string, RegExp, RegExp]> = [
      ["Pilotage", /Projets/, /Supervision/],
      ["Projet", /Tickets/, /Historique/],
      ["Outils", /Agents/, /Chat/],
    ];
    for (const [titre, premier, dernier] of groupes) {
      const intitule = screen.getByText(titre);
      expect(ordre(intitule, screen.getByRole("tab", { name: premier }))).toBe(
        true,
      );
      expect(ordre(intitule, screen.getByRole("tab", { name: dernier }))).toBe(
        true,
      );
    }
  });

  it("nomme chaque groupe comme une liste a part", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    for (const [titre, nombre] of [
      ["Pilotage", 3],
      ["Projet", 3],
      ["Outils", 3],
    ] as const) {
      const liste = screen.getByRole("list", { name: titre });
      expect(within(liste).getAllByRole("listitem")).toHaveLength(nombre);
    }
  });

  it("marque la destination active par aria-current", () => {
    render(<NavRail activePanel="files" onChangePanel={() => {}} />);
    expect(screen.getByRole("tab", { name: /Fichiers/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("tab", { name: /Tickets/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("remonte la destination En cours", async () => {
    const onChangePanel = vi.fn();
    render(<NavRail activePanel="projects" onChangePanel={onChangePanel} />);
    await userEvent.click(screen.getByRole("tab", { name: /En cours/ }));
    expect(onChangePanel).toHaveBeenCalledWith<[SidebarPanel]>("running");
  });

  it("porte le nombre d'apps sur En cours", () => {
    render(
      <NavRail activePanel="projects" onChangePanel={() => {}} appsEnCours={4} />,
    );
    expect(screen.getByLabelText("4 apps en cours")).toHaveTextContent("4");
  });

  it("n'affiche aucune pastille d'apps quand aucune ne tourne", () => {
    render(
      <NavRail activePanel="projects" onChangePanel={() => {}} appsEnCours={0} />,
    );
    expect(screen.queryByLabelText(/app/)).not.toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
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

describe("NavRail — le bouton Réglages (ticket-441)", () => {
  const notifications: ReglageDesNotifications = {
    active: true,
    etat: "bloquees",
    onChange: () => {},
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.orchestrator, "limits").mockResolvedValue({
      run_max_budget_usd: 1.5,
      llm_max_budget_usd: 0,
    });
  });

  function rendre() {
    render(
      <NavRail
        activePanel="projects"
        onChangePanel={() => {}}
        notifications={notifications}
      />,
    );
  }

  it("offers a Réglages button, outside the tab list", () => {
    rendre();

    const bouton = screen.getByRole("button", { name: "Réglages" });
    expect(bouton).toBeInTheDocument();
    expect(bouton).toHaveAttribute("aria-expanded", "false");
    expect(screen.getAllByRole("tab")).toHaveLength(9);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the panel holding the notification setting and the spending caps", async () => {
    rendre();

    await userEvent.click(screen.getByRole("button", { name: "Réglages" }));

    const panneau = screen.getByRole("dialog", { name: "Réglages" });
    expect(
      within(panneau).getByLabelText("Notifications système"),
    ).toBeInTheDocument();
    expect(within(panneau).getByText(/bloquées par le navigateur/)).toBeInTheDocument();
    expect(await within(panneau).findByText("$1.50")).toBeInTheDocument();
  });

  it("closes the panel on Escape", async () => {
    rendre();
    await userEvent.click(screen.getByRole("button", { name: "Réglages" }));

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the panel on a click outside", async () => {
    rendre();
    await userEvent.click(screen.getByRole("button", { name: "Réglages" }));

    await userEvent.click(screen.getByRole("tab", { name: /Agents/ }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("relays a change of the notification setting", async () => {
    const onChange = vi.fn();
    render(
      <NavRail
        activePanel="projects"
        onChangePanel={() => {}}
        notifications={{ ...notifications, etat: "actives", onChange }}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Réglages" }));

    await userEvent.click(screen.getByLabelText("Notifications système"));

    expect(onChange).toHaveBeenCalledWith(false);
  });
});

