import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NavRail from "./NavRail";
import type { ReglageDesNotifications } from "./ReglageNotifications";
import type { SidebarPanel } from "./panels";
import type { DonneesDeLaCloche } from "../../hooks/useNotificationsSysteme";
import { reglagesParDefaut } from "../../lib/reglagesNotifications";

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

  it("rend les dix destinations sans regression", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(10);
  });

  it("place En cours juste apres Projets", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const noms = screen.getAllByRole("tab").map((t) => t.textContent);
    expect(noms[0]).toMatch(/Projets/);
    expect(noms[1]).toMatch(/En cours/);
  });

  it("ordonne les dix destinations par groupe", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    const noms = screen.getAllByRole("tab").map((t) => t.textContent ?? "");
    const attendu = [
      "Projets",
      "En cours",
      "Supervision",
      "Rituels",
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
      ["Pilotage", /Projets/, /Rituels/],
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
      ["Pilotage", 4],
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

describe("NavRail — la cloche porte aussi le réglage global des notifications (ticket-779)", () => {
  const notifications: ReglageDesNotifications = {
    active: true,
    etat: "bloquees",
    onChange: () => {},
  };
  const cloche: DonneesDeLaCloche = {
    historique: [],
    nonLus: 0,
    toutMarquerLu: vi.fn(),
    reglages: reglagesParDefaut(),
    setReglage: vi.fn(),
    ouvrir: vi.fn(),
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders_the_settings_button_below_the_bell_outside_the_tablist", () => {
    // Ticket-810 : le bouton retiré par le ticket-779 revient, pour les réglages globaux.
    render(<NavRail activePanel="projects" onChangePanel={() => {}} notifications={notifications} cloche={cloche} />);

    const reglages = screen.getByRole("button", { name: "Réglages" });
    const cloc = screen.getByRole("button", { name: "Notifications" });
    expect(cloc.compareDocumentPosition(reglages) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("tablist", { name: "Navigation principale" })).not.toContainElement(reglages);
    expect(screen.getAllByRole("tab")).toHaveLength(10);
  });

  it("shows the global switch at the top of the bell's Réglages tab", async () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} notifications={notifications} cloche={cloche} />);

    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    await userEvent.click(screen.getByRole("tab", { name: "Réglages" }));

    const panneau = screen.getByRole("dialog", { name: "Notifications" });
    expect(within(panneau).getByLabelText("Notifications système")).toBeInTheDocument();
    expect(within(panneau).getByText(/bloquées par le navigateur/)).toBeInTheDocument();
  });

  it("relays a change of the global switch from the bell", async () => {
    const onChange = vi.fn();
    render(
      <NavRail
        activePanel="projects"
        onChangePanel={() => {}}
        notifications={{ ...notifications, etat: "actives", onChange }}
        cloche={cloche}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    await userEvent.click(screen.getByRole("tab", { name: "Réglages" }));

    await userEvent.click(screen.getByLabelText("Notifications système"));

    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("shows the bell with the unread count, outside the destinations", () => {
    const cloche: DonneesDeLaCloche = {
      historique: [],
      nonLus: 4,
      toutMarquerLu: vi.fn(),
      reglages: reglagesParDefaut(),
      setReglage: vi.fn(),
      ouvrir: vi.fn(),
    };
    render(<NavRail activePanel="projects" onChangePanel={() => {}} cloche={cloche} />);

    expect(screen.getByRole("button", { name: "Notifications, 4 non lues" })).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(10);
  });

  it("shows no bell without notification data", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} />);
    expect(screen.queryByRole("button", { name: /^Notifications/ })).not.toBeInTheDocument();
  });

  it("montre sur Rituels le nombre de rituels en retard", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} rituelsEnRetard={2} />);
    const onglet = screen.getByRole("tab", { name: /Rituels/ });
    expect(within(onglet).getByText("2")).toBeInTheDocument();
  });

  it("n'affiche aucune pastille sur Rituels quand rien n'est en retard", () => {
    render(<NavRail activePanel="projects" onChangePanel={() => {}} rituelsEnRetard={0} />);
    const onglet = screen.getByRole("tab", { name: /Rituels/ });
    expect(within(onglet).queryByText("0")).not.toBeInTheDocument();
    expect(onglet.querySelector("span[title]")).toBeNull();
  });
});
