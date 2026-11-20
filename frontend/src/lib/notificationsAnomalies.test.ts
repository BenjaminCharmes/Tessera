import { describe, expect, it } from "vitest";
import { notificationsPour, TYPES_NOTIF, type Instantane } from "./notifications";
import { completerReglages, estReglagesParType, reglagesParDefaut } from "./reglagesNotifications";
import { INITIAL } from "../hooks/streamState";
import type { Anomalie, RunActif } from "../types/api";

function anomalie(cle: string, over: Partial<Anomalie> = {}): Anomalie {
  return {
    regle: "silence", cle, ticket_id: "ticket-004", message: "Aucun événement depuis 15 min sur ce run.",
    mesure: 900, seuil: 900, unite: "s", ...over,
  };
}

function run(anomalies: Anomalie[] | undefined, id = "r1"): RunActif {
  return {
    run_id: id, project_id: "demineur", mode: "single", ticket_id: "ticket-004",
    etape: null, agent: null, tour: 1, tokens_entree: 0, tokens_sortie: 0,
    cout_usd: 0, verdict: null, demarre_a: "2026-11-05T08:00:00Z", anomalies,
  };
}

function instantane(r: RunActif): Instantane {
  return { runs: [r], etats: { [r.run_id]: { ...INITIAL, status: "running" } } };
}

const VIDE: Instantane = { runs: [], etats: {} };

describe("notificationsPour — anomalies (ticket-840)", () => {
  it("test_notificationsPour_reports_one_notification_for_a_new_anomaly", () => {
    const avant = instantane(run([]));
    const apres = instantane(run([anomalie("silence:1")]));

    const notifs = notificationsPour(avant, apres);

    expect(notifs).toHaveLength(1);
    expect(notifs[0]).toEqual({
      projectId: "demineur",
      type: "anomalie",
      titre: "demineur · ticket-004 : silence prolongé",
      corps: "Aucun événement depuis 15 min sur ce run.",
    });
  });

  it("test_notificationsPour_is_silent_when_the_anomaly_was_already_in_the_previous_snapshot", () => {
    const deja = [anomalie("silence:1")];

    expect(notificationsPour(instantane(run(deja)), instantane(run(deja)))).toEqual([]);
  });

  it("test_notificationsPour_without_a_previous_snapshot_reports_no_anomaly", () => {
    // À la connexion : ce qui existe déjà est la base, pas un message.
    expect(notificationsPour(VIDE, instantane(run([anomalie("silence:1")])))).toEqual([]);
  });

  it("test_notificationsPour_reports_two_notifications_for_two_new_anomalies", () => {
    const avant = instantane(run([anomalie("silence:1")]));
    const apres = instantane(
      run([anomalie("silence:1"), anomalie("tours:ticket-004", { regle: "tours_de_revue" }), anomalie("outil_repete:7", { regle: "outil_repete" })]),
    );

    const notifs = notificationsPour(avant, apres);

    expect(notifs.map((n) => n.titre)).toEqual([
      "demineur · ticket-004 : dernier tour de revue",
      "demineur · ticket-004 : outil répété",
    ]);
  });

  it("names an unknown rule by its raw identifier, without failing", () => {
    const notifs = notificationsPour(
      instantane(run([])),
      instantane(run([anomalie("x:1", { regle: "regle_future" })])),
    );

    expect(notifs[0]?.titre).toBe("demineur · ticket-004 : regle_future");
  });

  it("reads a backend that sends no anomalies at all as no anomaly", () => {
    expect(notificationsPour(instantane(run(undefined)), instantane(run(undefined)))).toEqual([]);
  });
});

describe("reglagesNotifications — anomalie (ticket-840)", () => {
  it("test_reglagesParDefaut_includes_anomalie", () => {
    expect(TYPES_NOTIF).toContain("anomalie");
    expect(reglagesParDefaut().anomalie).toEqual({ systeme: true, son: false });
  });

  it("test_estReglagesParType_accepts_a_stored_setting_without_anomalie", () => {
    const ancien: Partial<ReturnType<typeof reglagesParDefaut>> = { ...reglagesParDefaut() };
    delete ancien.anomalie;
    ancien.question = { systeme: false, son: true };

    expect(estReglagesParType(ancien)).toBe(true);
    const complet = completerReglages(ancien);
    // Les cases réglées par l'utilisateur survivent ; le type nouveau reçoit son défaut.
    expect(complet.question).toEqual({ systeme: false, son: true });
    expect(complet.anomalie).toEqual({ systeme: true, son: false });
  });

  it("still refuses a setting that lacks an older type, or that holds a wrong value", () => {
    const incomplet: Partial<ReturnType<typeof reglagesParDefaut>> = { ...reglagesParDefaut() };
    delete incomplet.quota_bas;

    expect(estReglagesParType(incomplet)).toBe(false);
    expect(estReglagesParType({ ...reglagesParDefaut(), anomalie: { systeme: "oui", son: false } })).toBe(false);
  });
});
