import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Cloche from "./Cloche";
import { useHistoriqueNotifications } from "../../hooks/useHistoriqueNotifications";
import type { DonneesDeLaCloche } from "../../hooks/useNotificationsSysteme";
import {
  ajouter,
  ecrireHistorique,
  historiqueVide,
} from "../../lib/historiqueNotifications";
import { reglagesParDefaut } from "../../lib/reglagesNotifications";

function donnees(surcharge: Partial<DonneesDeLaCloche> = {}): DonneesDeLaCloche {
  return {
    historique: [],
    nonLus: 0,
    toutMarquerLu: vi.fn(),
    reglages: reglagesParDefaut(),
    setReglage: vi.fn(),
    ouvrir: vi.fn(),
    ...surcharge,
  };
}

// La cloche branchée sur le vrai historique, pour voir le compteur retomber.
function Branchee({ ouvrir }: { ouvrir: (id: string) => void }) {
  const h = useHistoriqueNotifications();
  return (
    <Cloche
      cloche={donnees({
        historique: h.historique,
        nonLus: h.nonLus,
        toutMarquerLu: h.toutMarquerLu,
        ouvrir,
      })}
    />
  );
}

describe("Cloche", () => {
  beforeEach(() => window.localStorage.clear());

  function semer(): void {
    const maintenant = new Date();
    const h = ajouter(
      historiqueVide(maintenant),
      [
        { projectId: "demineur", type: "question", titre: "demineur : question", corps: "On casse ?" },
        { projectId: "serpent", type: "termine", titre: "serpent : terminé", corps: "fini" },
      ],
      maintenant,
    );
    ecrireHistorique(h);
  }

  it("shows the unread count on the bell", () => {
    render(<Cloche cloche={donnees({ nonLus: 3 })} />);
    const bouton = screen.getByRole("button", { name: "Notifications, 3 non lues" });
    expect(within(bouton).getByText("3")).toBeInTheDocument();
  });

  it("shows no badge when everything is read", () => {
    render(<Cloche cloche={donnees()} />);
    const bouton = screen.getByRole("button", { name: "Notifications" });
    expect(within(bouton).queryByText("0")).not.toBeInTheDocument();
  });

  it("keeps the violet badge as a background, never as a text colour", () => {
    render(<Cloche cloche={donnees({ nonLus: 1 })} />);
    const pastille = screen.getByText("1");
    expect(pastille.className).toMatch(/bg-violet-/);
    expect(pastille.className).not.toMatch(/text-violet-/);
  });

  it("lists the day's notifications, unread in bold, and opens the project on click", async () => {
    semer();
    const ouvrir = vi.fn();
    render(<Branchee ouvrir={ouvrir} />);
    await userEvent.click(screen.getByRole("button", { name: /Notifications/ }));

    const liste = screen.getByRole("list", { name: "Notifications du jour" });
    const lignes = within(liste).getAllByRole("button");
    expect(lignes).toHaveLength(2);
    // Du plus récent au plus ancien : « terminé » a été ajouté en dernier.
    expect(lignes[0]).toHaveTextContent("serpent : terminé");
    expect(within(lignes[0]).getByText("serpent : terminé").className).toMatch(/font-semibold/);

    await userEvent.click(lignes[1]);
    expect(ouvrir).toHaveBeenCalledWith("demineur");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("resets the counter to zero on mark all read", async () => {
    semer();
    render(<Branchee ouvrir={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Notifications, 2 non lues" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Notifications/ }));

    await userEvent.click(screen.getByRole("button", { name: "Tout marquer comme lu" }));

    expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
    const liste = screen.getByRole("list", { name: "Notifications du jour" });
    expect(within(liste).getByText("serpent : terminé").className).not.toMatch(/font-semibold/);
  });

  it("says so when nothing happened today", async () => {
    render(<Cloche cloche={donnees()} />);
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    expect(screen.getByText("Rien depuis minuit.")).toBeInTheDocument();
  });

  it("offers one row per event type with a System and a Sound box", async () => {
    const setReglage = vi.fn();
    render(<Cloche cloche={donnees({ setReglage })} />);
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    await userEvent.click(screen.getByRole("tab", { name: "Réglages" }));

    expect(screen.getAllByRole("checkbox")).toHaveLength(14);
    const systeme = screen.getByLabelText("Question d'un agent : système");
    const son = screen.getByLabelText("Question d'un agent : son");
    expect(systeme).toBeChecked();
    expect(son).toBeChecked();
    expect(screen.getByLabelText("Run terminé : son")).not.toBeChecked();

    await userEvent.click(systeme);
    expect(setReglage).toHaveBeenCalledWith("question", "systeme", false);
  });

  it("closes on Escape", async () => {
    render(<Cloche cloche={donnees()} />);
    await userEvent.click(screen.getByRole("button", { name: "Notifications" }));
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
