import { describe, expect, it } from "vitest";
import { notificationsPour, type Instantane } from "./notifications";
import { INITIAL, type StreamState } from "../hooks/streamState";
import type { SanteAgent } from "./santeAgent";
import type { RunActif } from "../types/api";

function run(id: string, project = "demineur"): RunActif {
  return {
    run_id: id, project_id: project, mode: "single", ticket_id: "ticket-004",
    etape: null, agent: null, tour: 1, tokens_entree: 0, tokens_sortie: 0,
    cout_usd: 0, verdict: null, demarre_a: "2026-09-26T08:00:00Z",
  };
}

const AILLEURS = { projetActif: "ide-core", visible: true };
const VIDE: Instantane = { runs: [], etats: {} };

describe("notificationsPour", () => {
  it("annonce une question d'agent en nommant le projet et le ticket", () => {
    // Une question expire (ADR-025) pendant qu'on est ailleurs : c'est le cas
    // que le ticket existe pour couvrir.
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } };
    const apres: Instantane = {
      runs: [run("r1")],
      etats: { r1: { ...INITIAL, status: "running", pendingQuestion: "On casse l'API ?" } },
    };
    const [n] = notificationsPour(avant, apres, AILLEURS);
    expect(n.titre).toBe("demineur · ticket-004 : un agent pose une question");
    expect(n.corps).toBe("On casse l'API ?");
  });

  it("n'annonce rien pour un agent qui finit son tour", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: "codeur" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: null, appels: 1 } } };
    expect(notificationsPour(avant, apres, AILLEURS)).toEqual([]);
  });

  it("annonce un run bloqué et un run terminé", () => {
    const bloque = notificationsPour(
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } },
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "error", errorMessage: "budget" } } },
      AILLEURS,
    );
    expect(bloque[0].titre).toMatch(/bloqué/);

    const fini = notificationsPour(
      {
        runs: [run("r1")],
        etats: { r1: { ...INITIAL, status: "done", lastResult: { ticket_id: "ticket-004", final_status: "done", rounds: 2, approved: true } as never } },
      },
      VIDE,
      AILLEURS,
    );
    expect(fini[0].titre).toBe("demineur · ticket-004 : terminé");
    expect(fini[0].corps).toBe("ticket-004 approuvé en 2 tours");
  });

  describe("agent figé (ticket-553)", () => {
    function instantane(sante: SanteAgent): Instantane {
      const etat: StreamState = { ...INITIAL, status: "running", currentAgent: "codeur" };
      return { runs: [run("r1")], etats: { r1: etat }, sante: { r1: sante } };
    }

    it("annonce le passage de silencieux à figé", () => {
      const notifs = notificationsPour(instantane("attente"), instantane("blocage_suspecte"), AILLEURS);
      expect(notifs).toHaveLength(1);
      expect(notifs[0].titre).toBe("demineur · ticket-004 : un agent semble figé");
      expect(notifs[0].corps).toMatch(/codeur/);
    });

    it("ne prévient qu'une fois tant que l'agent reste figé", () => {
      const fige = instantane("blocage_suspecte");
      expect(notificationsPour(fige, fige, AILLEURS)).toEqual([]);
    });

    it("prévient de nouveau quand l'agent a repris puis se fige encore", () => {
      const premiere = notificationsPour(instantane("attente"), instantane("blocage_suspecte"), AILLEURS);
      const reprise = notificationsPour(instantane("blocage_suspecte"), instantane("actif"), AILLEURS);
      const seconde = notificationsPour(instantane("actif"), instantane("blocage_suspecte"), AILLEURS);
      expect(premiere).toHaveLength(1);
      expect(reprise).toEqual([]);
      expect(seconde).toHaveLength(1);
    });

    it("se tait quand le projet est affiché et la fenêtre visible", () => {
      const avant = instantane("attente");
      const apres = instantane("blocage_suspecte");
      expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: true })).toEqual([]);
      expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: false })).toHaveLength(1);
    });

    it("ne dit rien d'un instantané sans santé", () => {
      expect(notificationsPour(VIDE, { runs: [run("r1")], etats: { r1: INITIAL } }, AILLEURS)).toEqual([]);
    });
  });

  describe("livraison", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "done" } } };
    const apresAvec = (ciMerge: { merged: boolean; arret: string | null }, pr: number | null = null): Instantane => ({
      runs: [run("r1")],
      etats: { r1: { ...INITIAL, status: "done", ciMerge, livraisonPrNumber: pr } },
    });

    it("annonce une PR mergée avec son numéro", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: true, arret: null }, 42), AILLEURS);
      expect(n.titre).toBe("demineur · ticket-004 : PR mergée");
      expect(n.corps).toContain("#42");
    });

    it("annonce une PR non mergée avec sa raison", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: false, arret: "CI rouge, PR laissée ouverte" }), AILLEURS);
      expect(n.titre).toBe("demineur · ticket-004 : PR non mergée");
      expect(n.corps).toBe("CI rouge, PR laissée ouverte");
    });

    it("donne un texte de repli sans raison", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: false, arret: null }), AILLEURS);
      expect(n.corps).not.toBe("");
    });

    it("n'annonce pas deux fois la même issue", () => {
      const apres = apresAvec({ merged: true, arret: null });
      expect(notificationsPour(apres, apres, AILLEURS)).toEqual([]);
    });

    it("annonce l'issue de chaque ticket d'une file, pas seulement la première", () => {
      const file = (ciMerge: { merged: boolean; arret: string | null }): Instantane => ({
        runs: [{ ...run("r1"), mode: "queue" }],
        etats: { r1: { ...INITIAL, status: "running", ciMerge } },
      });
      const premiere = file({ merged: true, arret: null });
      const seconde = file({ merged: false, arret: "CI rouge" });
      const [n] = notificationsPour(premiere, seconde, AILLEURS);
      expect(n.titre).toBe("demineur · ticket-004 : PR non mergée");
      expect(n.corps).toBe("CI rouge");
    });

    it("se tait quand le projet est affiché et la fenêtre visible", () => {
      const apres = apresAvec({ merged: false, arret: "refusé" });
      expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: true })).toEqual([]);
      expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: false })).toHaveLength(1);
    });
  });

  it("se tait quand la fenêtre est visible et le projet affiché", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", pendingQuestion: "?" } } };
    expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: true })).toEqual([]);
    expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: false })).toHaveLength(1);
  });
});
