import { describe, expect, it } from "vitest";
import { clotureDuRun, etatAffiche, issueAffichee } from "./etatDuRun";
import { INITIAL } from "../../hooks/streamState";

describe("etatAffiche", () => {
  it("says blocked on an error, ahead of a pending question", () => {
    expect(etatAffiche({ ...INITIAL, status: "error", pendingQuestion: "?" })).toEqual({
      etat: "echec",
      libelle: "bloqué",
    });
  });

  it("says it waits for an answer", () => {
    expect(etatAffiche({ ...INITIAL, pendingQuestion: "?" })).toEqual({
      etat: "attention",
      libelle: "attend une réponse",
    });
  });

  it("names the working agent, or says running", () => {
    expect(etatAffiche({ ...INITIAL, currentAgent: "codeur" }).libelle).toBe("codeur");
    expect(etatAffiche(INITIAL)).toEqual({ etat: "en-cours", libelle: "en cours" });
  });
});

describe("issueAffichee", () => {
  it("has no word for a running run", () => {
    expect(issueAffichee("en-cours")).toBeNull();
  });

  it("gives a word and a state to every closed outcome", () => {
    expect(issueAffichee("termine")).toEqual({ etat: "reussi", libelle: "terminé" });
    expect(issueAffichee("bloque")?.etat).toBe("echec");
    expect(issueAffichee("erreur")?.libelle).toBe("en erreur");
    expect(issueAffichee("autre")?.etat).toBe("neutre");
  });
});

describe("clotureDuRun", () => {
  it("reads the run_closed timestamp, and nothing while the run runs", () => {
    const clos = {
      ...INITIAL,
      events: [{ type: "run_closed" as const, agent: null, ticket_id: "ticket-001", data: {}, timestamp: "2026-10-26T10:05:00.000Z" }],
    };

    expect(clotureDuRun(clos)).toBe("2026-10-26T10:05:00.000Z");
    expect(clotureDuRun(INITIAL)).toBeUndefined();
  });
});
