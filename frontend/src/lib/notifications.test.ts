import { describe, expect, it } from "vitest";
import { masqueeParToast, notificationsPour, type Instantane } from "./notifications";
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
    const [n] = notificationsPour(avant, apres);
    expect(n.titre).toBe("demineur · ticket-004 : un agent pose une question");
    expect(n.corps).toBe("On casse l'API ?");
  });

  it("n'annonce rien pour un agent qui finit son tour", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: "codeur" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: null, appels: 1 } } };
    expect(notificationsPour(avant, apres)).toEqual([]);
  });

  it("annonce un run bloqué et un run terminé", () => {
    const bloque = notificationsPour(
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } },
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "error", errorMessage: "budget" } } });
    expect(bloque[0].titre).toMatch(/bloqué/);

    const fini = notificationsPour(
      {
        runs: [run("r1")],
        etats: { r1: { ...INITIAL, status: "done", lastResult: { ticket_id: "ticket-004", final_status: "done", rounds: 2, approved: true } as never } },
      },
      VIDE);
    expect(bloque[0].type).toBe("bloque");
    expect(fini[0].type).toBe("termine");
    expect(fini[0].titre).toBe("demineur · ticket-004 : terminé");
    expect(fini[0].corps).toBe("ticket-004 approuvé en 2 tours");
  });

  describe("agent figé (ticket-553)", () => {
    function instantane(sante: SanteAgent): Instantane {
      const etat: StreamState = { ...INITIAL, status: "running", currentAgent: "codeur" };
      return { runs: [run("r1")], etats: { r1: etat }, sante: { r1: sante } };
    }

    it("annonce le passage de silencieux à figé", () => {
      const notifs = notificationsPour(instantane("attente"), instantane("blocage_suspecte"));
      expect(notifs).toHaveLength(1);
      expect(notifs[0].titre).toBe("demineur · ticket-004 : un agent semble figé");
      expect(notifs[0].corps).toMatch(/codeur/);
      expect(notifs[0].type).toBe("fige");
    });

    it("ne prévient qu'une fois tant que l'agent reste figé", () => {
      const fige = instantane("blocage_suspecte");
      expect(notificationsPour(fige, fige)).toEqual([]);
    });

    it("prévient de nouveau quand l'agent a repris puis se fige encore", () => {
      const premiere = notificationsPour(instantane("attente"), instantane("blocage_suspecte"));
      const reprise = notificationsPour(instantane("blocage_suspecte"), instantane("actif"));
      const seconde = notificationsPour(instantane("actif"), instantane("blocage_suspecte"));
      expect(premiere).toHaveLength(1);
      expect(reprise).toEqual([]);
      expect(seconde).toHaveLength(1);
    });

    it("ne prévient pas pendant une étape silencieuse, même si la santé dit figé (ticket-587)", () => {
      for (const etape of ["tests", "securite", "validation", "documentation", "livraison"]) {
        const etat: StreamState = { ...INITIAL, status: "running", etapesEnCours: [etape] };
        const silencieux = (sante: SanteAgent): Instantane => ({
          runs: [run("r1")], etats: { r1: etat }, sante: { r1: sante },
        });
        expect(notificationsPour(silencieux("attente"), silencieux("blocage_suspecte"))).toEqual([]);
      }
    });

    it("garde la notification du projet affiché, que seul le toast masque", () => {
      const avant = instantane("attente");
      const apres = instantane("blocage_suspecte");
      const notifs = notificationsPour(avant, apres);
      expect(notifs).toHaveLength(1);
      expect(masqueeParToast(notifs[0], { projetActif: "demineur", visible: true })).toBe(true);
    });

    it("ne dit rien d'un instantané sans santé", () => {
      expect(notificationsPour(VIDE, { runs: [run("r1")], etats: { r1: INITIAL } })).toEqual([]);
    });
  });

  describe("livraison", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "done" } } };
    const apresAvec = (ciMerge: { merged: boolean; arret: string | null }, pr: number | null = null): Instantane => ({
      runs: [run("r1")],
      etats: { r1: { ...INITIAL, status: "done", ciMerge, livraisonPrNumber: pr } },
    });

    it("annonce une PR mergée avec son numéro", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: true, arret: null }, 42));
      expect(n.titre).toBe("demineur · ticket-004 : PR mergée");
      expect(n.corps).toContain("#42");
      expect(n.type).toBe("merge");
    });

    it("annonce une PR non mergée avec sa raison", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: false, arret: "CI rouge, PR laissée ouverte" }));
      expect(n.titre).toBe("demineur · ticket-004 : PR non mergée");
      expect(n.corps).toBe("CI rouge, PR laissée ouverte");
      expect(n.type).toBe("ci_rouge");
    });

    it("donne un texte de repli sans raison", () => {
      const [n] = notificationsPour(avant, apresAvec({ merged: false, arret: null }));
      expect(n.corps).not.toBe("");
    });

    it("n'annonce pas deux fois la même issue", () => {
      const apres = apresAvec({ merged: true, arret: null });
      expect(notificationsPour(apres, apres)).toEqual([]);
    });

    it("annonce l'issue de chaque ticket d'une file, pas seulement la première", () => {
      const file = (ciMerge: { merged: boolean; arret: string | null }): Instantane => ({
        runs: [{ ...run("r1"), mode: "queue" }],
        etats: { r1: { ...INITIAL, status: "running", ciMerge } },
      });
      const premiere = file({ merged: true, arret: null });
      const seconde = file({ merged: false, arret: "CI rouge" });
      const [n] = notificationsPour(premiere, seconde);
      expect(n.titre).toBe("demineur · ticket-004 : PR non mergée");
      expect(n.corps).toBe("CI rouge");
    });

    it("garde la notification du projet affiché, que seul le toast masque", () => {
      const apres = apresAvec({ merged: false, arret: "refusé" });
      const notifs = notificationsPour(avant, apres);
      expect(notifs).toHaveLength(1);
      expect(masqueeParToast(notifs[0], { projetActif: "demineur", visible: true })).toBe(true);
    });
  });

  it("garde la notification du projet affiché, que seul le toast masque", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", pendingQuestion: "?" } } };
    const [n] = notificationsPour(avant, apres);
    expect(n.type).toBe("question");
    expect(masqueeParToast(n, { projetActif: "demineur", visible: true })).toBe(true);
    expect(masqueeParToast(n, { projetActif: "demineur", visible: false })).toBe(false);
    expect(masqueeParToast(n, { projetActif: "ide-core", visible: true })).toBe(false);
  });
});
