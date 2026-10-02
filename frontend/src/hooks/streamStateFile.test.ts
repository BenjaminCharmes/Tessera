import { describe, it, expect } from "vitest";
import { applyEvent, etatDepuisRun, INITIAL, clearTokensForReplay } from "./streamState";
import type { OrchestratorEvent, RunActif } from "../types/api";
import type { EntreeSecurite, EntreeValidateur } from "./streamState";

function ev(over: Partial<OrchestratorEvent>): OrchestratorEvent {
  return {
    type: "agent_started",
    agent: "codeur",
    ticket_id: "ticket-012",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "r1",
    project_id: "demineur",
    ...over,
  } as OrchestratorEvent;
}

/** L'état d'un run de file arrivé au bout du ticket-012. */
function apresLePremierTicket() {
  let s = INITIAL;
  s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-012", data: { index: 1, total: 3 } }));
  s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
  s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer" }));
  s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED" } }));
  s = applyEvent(s, ev({ type: "agent_question", data: { question: "on casse l'API ?" } }));
  s = applyEvent(s, ev({ type: "quota_updated", data: { utilization: 0.4 } }));
  return s;
}

describe("applyEvent — un ticket de file n'hérite pas du précédent (ticket-180)", () => {
  it("remet les entries à zéro pour le nouveau ticket", () => {
    // Le bloc reviewer de ticket-012 restait affiché sous le codeur de
    // ticket-013, verdict APPROVED compris — c'est `entries` qui pilote
    // l'affichage, pas `events`.
    const avant = apresLePremierTicket();

    const apres = applyEvent(
      avant,
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.entries).toEqual([]);
  });

  it("garde les événements des tickets précédents dans la file (ticket-283)", () => {
    // `events` alimente le Pipeline log : effacer l'historique d'un ticket
    // précédent efface son journal de la vue, alors que c'est un seul run.
    const avant = apresLePremierTicket();

    const apres = applyEvent(
      avant,
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(
      apres.events.some((e) => e.type === "agent_done" && e.agent === "reviewer"),
    ).toBe(true);
  });

  it("oublie l'agent courant et le tour du ticket précédent", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.currentAgent).toBeNull();
    expect(apres.currentRound).toBe(0);
  });

  it("oublie une question restée en attente", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.pendingQuestion).toBeNull();
  });

  it("garde ce qui appartient au run : avancement et quota", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.queue).toEqual({ index: 2, total: 3 });
    expect(apres.quota).not.toBeNull();
  });

  it("prend le ticket annoncé et reste en cours", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.ticketId).toBe("ticket-013");
    expect(apres.status).toBe("running");
  });
});

describe("applyEvent — fil chronologique des passages (ticket-222)", () => {
  it("garde le verdict du reviewer au tour 1 après agent_started du codeur au tour 2", () => {
    let s = INITIAL;
    // Tour 1 : codeur puis reviewer
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "Implémentation terminée." } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "CHANGES_REQUESTED\nAjoute des tests." } }));
    // Tour 2 : le codeur reprend
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 2 } }));

    // Le verdict du reviewer du tour 1 doit rester dans les entrées.
    const reviewerEntry = s.entries.find((e) => e.genre === "agent" && e.agent === "reviewer" && e.isDone);
    expect(reviewerEntry).toBeDefined();
    expect(reviewerEntry?.genre === "agent" ? reviewerEntry.content : "").toContain("CHANGES_REQUESTED");
  });

  it("un run à deux tours produit quatre entrées dans l'ordre codeur, reviewer, codeur, reviewer", () => {
    let s = INITIAL;
    // Tour 1
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "v1" } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "CHANGES_REQUESTED" } }));
    // Tour 2
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 2 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "v2" } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 2 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED" } }));

    expect(s.entries).toHaveLength(4);
    expect(s.entries.map((e) => (e.genre === "agent" ? e.agent : e.genre))).toEqual([
      "codeur", "reviewer", "codeur", "reviewer",
    ]);
  });
});

describe("applyEvent — ticket_id depuis ev.ticket_id et run_closed (ticket-267)", () => {
  it("lit le ticket_id au premier niveau de l'evenement, pas seulement dans data", () => {
    // Le backend émet ticket_id en champ racine de l'événement ; data["ticket_id"]
    // est un doublon de confort absent de certains backends.
    const s = applyEvent(
      INITIAL,
      ev({
        type: "pipeline_done",
        ticket_id: "ticket-267",
        data: { approved: true, rounds: 1, final_status: "done" },
      }),
    );
    expect(s.lastResult?.ticket_id).toBe("ticket-267");
  });

  it("marque runClosed a true sur run_closed", () => {
    const s = applyEvent(INITIAL, ev({ type: "run_closed" }));
    expect(s.runClosed).toBe(true);
  });

  it("runClosed reste false apres pipeline_done", () => {
    // Entre pipeline_done et run_closed, la livraison tourne encore.
    const s = applyEvent(
      INITIAL,
      ev({
        type: "pipeline_done",
        ticket_id: "ticket-267",
        data: { approved: true, rounds: 1, final_status: "done" },
      }),
    );
    expect(s.runClosed).toBe(false);
  });
});

describe("applyEvent — entrées securite et validateur dans le fil (ticket-257)", () => {
  it("security_audit_done ajoute une EntreeSecurite avec le verdict", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "ok" } }));
    s = applyEvent(s, ev({
      type: "security_audit_done",
      agent: null,
      data: { verdict: "APPROVED", summary: "Aucune faille détectée.", issues_count: 0, reason: "" },
    }));

    expect(s.entries).toHaveLength(2);
    const auditEntry = s.entries[1] as EntreeSecurite;
    expect(auditEntry.genre).toBe("securite");
    expect(auditEntry.verdict).toBe("APPROVED");
    expect(auditEntry.summary).toBe("Aucune faille détectée.");
    expect(auditEntry.isDone).toBe(true);
  });

  it("validation_done ajoute une EntreeValidateur avec ses critères", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "ok" } }));
    s = applyEvent(s, ev({
      type: "validation_done",
      agent: null,
      data: {
        verdict: "CHANGES_REQUESTED",
        feedback: "Deux critères échoués.",
        criteria: [
          { criterion: "Tests unitaires", passed: false, note: "Aucun test pour foo()." },
          { criterion: "Typage", passed: true, note: "" },
        ],
      },
    }));

    expect(s.entries).toHaveLength(2);
    const validEntry = s.entries[1] as EntreeValidateur;
    expect(validEntry.genre).toBe("validateur");
    expect(validEntry.verdict).toBe("CHANGES_REQUESTED");
    expect(validEntry.feedback).toBe("Deux critères échoués.");
    expect(validEntry.criteria).toHaveLength(2);
    expect(validEntry.criteria[0]).toEqual({
      criterion: "Tests unitaires",
      passed: false,
      note: "Aucun test pour foo().",
    });
    expect(validEntry.isDone).toBe(true);
  });
});

describe("applyEvent — run_closed remet etape a null (ticket-279)", () => {
  it("etape vaut null apres run_closed suite a livraison_started", () => {
    let s = applyEvent(INITIAL, ev({ type: "livraison_started" }));
    expect(s.etape).toBe("livraison");
    s = applyEvent(s, ev({ type: "run_closed" }));
    expect(s.etape).toBeNull();
  });

  it("etape vaut null apres run_closed suite a documentation_started", () => {
    let s = applyEvent(INITIAL, ev({ type: "documentation_started" }));
    expect(s.etape).toBe("documentation");
    s = applyEvent(s, ev({ type: "run_closed" }));
    expect(s.etape).toBeNull();
  });
});

describe("applyEvent — coût en direct (ticket-197)", () => {
  it("cumule le coût et compte les appels, et remet les outils à zéro par agent", () => {
    let s = applyEvent(INITIAL, ev({ type: "agent_started", agent: "codeur", data: {} }));
    s = applyEvent(s, ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Read" } }));
    s = applyEvent(s, ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Edit" } }));
    expect(s.outils).toBe(2);
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "", cost_usd: 0.4 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: {} }));
    expect(s.outils).toBe(0);
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED", cost_usd: 0.2 } }));
    expect(s.coutUsd).toBeCloseTo(0.6);
    expect(s.appels).toBe(2);
  });
});

describe("applyEvent — etapesEnCours pour le parallélisme (ticket-290)", () => {
  it("ajoute revue et validation à etapesEnCours quand les deux démarrent", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "validation_started", data: {} }));

    expect(s.etapesEnCours).toContain("revue");
    expect(s.etapesEnCours).toContain("validation");
  });

  it("retire validation de etapesEnCours après validation_done, laisse revue", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "validation_started", data: {} }));
    s = applyEvent(s, ev({ type: "validation_done", data: { approved: true, criteria: [] } }));

    expect(s.etapesEnCours).not.toContain("validation");
    expect(s.etapesEnCours).toContain("revue");
  });
});

describe("etatDepuisRun — lecture de etapes_en_cours (ticket-290)", () => {
  const baseRun: RunActif = {
    run_id: "r1",
    project_id: "proj",
    mode: "single",
    ticket_id: "ticket-290",
    etape: "revue",
    agent: "reviewer",
    tour: 1,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
  };

  it("lit etapes_en_cours depuis l'instantané quand présent", () => {
    const run: RunActif = { ...baseRun, etapes_en_cours: ["revue", "validation"] };
    const s = etatDepuisRun(run);
    expect(s.etapesEnCours).toEqual(["revue", "validation"]);
  });

  it("retombe sur [etape] quand etapes_en_cours est absent", () => {
    const s = etatDepuisRun(baseRun);
    expect(s.etapesEnCours).toEqual(["revue"]);
  });

  it("retombe sur [] quand etapes_en_cours est absent et etape est null", () => {
    const run: RunActif = { ...baseRun, etape: null };
    const s = etatDepuisRun(run);
    expect(s.etapesEnCours).toEqual([]);
  });
});

describe("applyEvent — ticketEvents séparé du journal du run (ticket-313)", () => {
  it("ticketEvents ne contient pas security_audit_done du ticket précédent", () => {
    // Dans une file, StageStrip utilise ticketEvents : les étapes du ticket A
    // ne doivent pas apparaître comme « done » pour le ticket B.
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-A", data: { index: 1, total: 2 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({
      type: "security_audit_done",
      agent: null,
      data: { verdict: "APPROVED", summary: "ok", issues_count: 0, reason: "" },
    }));

    // Ticket B démarre
    s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-B", data: { index: 2, total: 2 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));

    // ticketEvents ne voit pas l'audit du ticket A
    expect(s.ticketEvents.some((e) => e.type === "security_audit_done")).toBe(false);
  });

  it("events (Pipeline log) conserve les événements du ticket A après queue_progress", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-A", data: { index: 1, total: 2 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "ok" } }));

    s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-B", data: { index: 2, total: 2 } }));

    // events garde tout pour le Pipeline log
    expect(s.events.some((e) => e.type === "agent_done" && e.agent === "codeur")).toBe(true);
    // ticketEvents repart propre
    expect(s.ticketEvents.some((e) => e.type === "agent_done")).toBe(false);
  });

  it("ticketEvents s'accumule normalement entre deux queue_progress", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-B", data: { index: 2, total: 2 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "security_audit_started", data: {} }));

    expect(s.ticketEvents.some((e) => e.type === "agent_started")).toBe(true);
    expect(s.ticketEvents.some((e) => e.type === "security_audit_started")).toBe(true);
  });
});

describe("clearTokensForReplay — rejeu sans doublon (ticket-313)", () => {
  it("le même lot de agent_token reçu deux fois ne double pas le texte", () => {
    // Simule un aller-retour dans la Supervision : le backend rejoue les tokens
    // à chaque abonnement. clearTokensForReplay vide les tokens avant le rejeu
    // pour que le résultat soit identique à la première visite.
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_token", agent: "codeur", data: { token: "bonjour" } }));

    // Vider avant le rejeu (ce que useSupervision fait à l'abonnement)
    s = clearTokensForReplay(s);

    // Même token arrive à nouveau (rejeu)
    s = applyEvent(s, ev({ type: "agent_token", agent: "codeur", data: { token: "bonjour" } }));

    const codeurEntry = s.entries.find((e) => e.genre === "agent" && e.agent === "codeur");
    expect(codeurEntry?.genre === "agent" ? codeurEntry.tokens : "").toBe("bonjour");
  });

  it("ne touche pas aux entrées déjà terminées (isDone)", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_token", agent: "codeur", data: { token: "hello" } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "Résultat final." } }));

    s = clearTokensForReplay(s);

    const doneEntry = s.entries.find((e) => e.genre === "agent" && e.isDone);
    // content (issu de agent_done) est préservé ; seuls les tokens en live sont effacés
    expect(doneEntry?.genre === "agent" ? doneEntry.content : "").toBe("Résultat final.");
  });

  it("vide currentTokens en plus des entrées", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_token", agent: "codeur", data: { token: "abc" } }));
    expect(s.currentTokens).toBe("abc");

    s = clearTokensForReplay(s);
    expect(s.currentTokens).toBe("");
  });
});

describe("applyEvent — livraison_done et ci_merge_done (ticket-308)", () => {
  it("livraison_done capture le pr_number", () => {
    const s = applyEvent(
      INITIAL,
      ev({
        type: "livraison_done",
        agent: null,
        data: { pr_number: 42, merged: false, arret: null },
      }),
    );
    expect(s.livraisonPrNumber).toBe(42);
  });

  it("livraison_done sans pr_number laisse livraisonPrNumber a null", () => {
    const s = applyEvent(
      INITIAL,
      ev({ type: "livraison_done", agent: null, data: {} }),
    );
    expect(s.livraisonPrNumber).toBeNull();
  });

  it("ci_merge_done avec merged: true marque la fusion", () => {
    let s = applyEvent(
      INITIAL,
      ev({ type: "livraison_done", agent: null, data: { pr_number: 10 } }),
    );
    s = applyEvent(
      s,
      ev({
        type: "ci_merge_done",
        agent: null,
        data: { pr_number: 10, merged: true, arret: null },
      }),
    );
    expect(s.ciMerge).toEqual({ merged: true, arret: null });
  });

  it("ci_merge_done avec merged: false conserve l'arret", () => {
    let s = applyEvent(
      INITIAL,
      ev({ type: "livraison_done", agent: null, data: { pr_number: 7 } }),
    );
    s = applyEvent(
      s,
      ev({
        type: "ci_merge_done",
        agent: null,
        data: { pr_number: 7, merged: false, arret: "CI rouge : la PR #7 reste ouverte." },
      }),
    );
    expect(s.ciMerge).toEqual({ merged: false, arret: "CI rouge : la PR #7 reste ouverte." });
  });

  it("ciMerge reste null avant ci_merge_done", () => {
    const s = applyEvent(
      INITIAL,
      ev({ type: "livraison_done", agent: null, data: { pr_number: 5 } }),
    );
    expect(s.ciMerge).toBeNull();
  });
});

describe("applyEvent — answer_ack (ticket-320)", () => {
  it("enregistre l'accusé de réception d'une réponse déposée", () => {
    const s = applyEvent(
      INITIAL,
      ev({ type: "answer_ack", agent: null, data: { outcome: "deposited" } }),
    );
    expect(s.answerAck).toBe("deposited");
  });

  it("enregistre l'accusé de réception d'une réponse transmise", () => {
    const s = applyEvent(
      INITIAL,
      ev({ type: "answer_ack", agent: null, data: { outcome: "transmitted" } }),
    );
    expect(s.answerAck).toBe("transmitted");
  });

  it("efface l'accusé quand une nouvelle question arrive", () => {
    let s = applyEvent(
      INITIAL,
      ev({ type: "answer_ack", agent: null, data: { outcome: "deposited" } }),
    );
    s = applyEvent(
      s,
      ev({ type: "agent_question", data: { question: "On casse l'API ?" } }),
    );
    expect(s.answerAck).toBeNull();
  });

  it("efface l'accusé quand l'agent reprend (agent_token)", () => {
    let s = applyEvent(
      INITIAL,
      ev({ type: "answer_ack", agent: null, data: { outcome: "transmitted" } }),
    );
    s = applyEvent(
      s,
      ev({ type: "agent_token", agent: "codeur", data: { token: "…" } }),
    );
    expect(s.answerAck).toBeNull();
  });
});
