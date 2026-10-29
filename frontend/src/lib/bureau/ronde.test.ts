import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import {
  DUREE_DE_VISITE_MS,
  ECART_ENTRE_VISITES_MS,
  MEMOIRE_VIERGE,
  ronde,
} from "./ronde";
import type { DemandeDeVisite, MemoireDeRonde } from "./ronde";

const T0 = Date.parse("2026-10-29T10:00:00.000Z");
const TICK = 5_000;

function ev(
  type: OrchestratorEvent["type"],
  a: number,
  agent: OrchestratorEvent["agent"] = null,
  data: Record<string, unknown> = {},
): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: new Date(a).toISOString() };
}

/** Le codeur démarre à l'instant `a` : un seul poste occupé, dernier événement à `a`. */
function enCodage(a: number): StreamState {
  return [ev("agent_started", a, "codeur")].reduce(applyEvent, INITIAL);
}

function enQuestion(a: number): StreamState {
  return [ev("agent_started", a, "codeur"), ev("agent_question", a, null, { question: "Quelle option ?" })].reduce(
    applyEvent,
    INITIAL,
  );
}

function clos(a: number): StreamState {
  return [ev("agent_started", a, "codeur"), ev("run_closed", a)].reduce(applyEvent, INITIAL);
}

interface Projet {
  nom: string;
  etat: StreamState;
}

/** Rejoue des ticks de 5 s de `de` à `a` ; rend la mémoire finale et les départs vus (un par `depuis`). */
function rejouer(
  projets: readonly Projet[],
  de: number,
  a: number,
  demande: DemandeDeVisite | null = null,
  depart: MemoireDeRonde = MEMOIRE_VIERGE,
): { memoire: MemoireDeRonde; departs: string[] } {
  const departs: string[] = [];
  let memoire = depart;
  for (let t = de; t <= a; t += TICK) {
    memoire = ronde(memoire, projets, demande, t);
    const v = memoire.visite;
    if (v && !departs.includes(`${v.projet}@${v.depuis}`)) departs.push(`${v.projet}@${v.depuis}`);
  }
  return { memoire, departs };
}

describe("ronde", () => {
  it("keeps the director at his desk while the run is active", () => {
    const { memoire, departs } = rejouer([{ nom: "a", etat: enCodage(T0) }], T0 + TICK, T0 + 25_000);

    expect(memoire.visite).toBeNull();
    expect(departs).toEqual([]);
  });

  it("sends him behind the busy agent of a run that goes silent, then back after the visit", () => {
    const projets = [{ nom: "a", etat: enCodage(T0) }];
    const { memoire } = rejouer(projets, T0 + TICK, T0 + 30_000 + TICK);

    expect(memoire.visite).toEqual({ projet: "a", poste: "codeur", depuis: T0 + 35_000 });

    const encore = ronde(memoire, projets, null, T0 + 35_000 + DUREE_DE_VISITE_MS - TICK);
    expect(encore.visite).not.toBeNull();
    const revenu = ronde(encore, projets, null, T0 + 35_000 + DUREE_DE_VISITE_MS);
    expect(revenu.visite).toBeNull();
  });

  it("also goes for a run that turns frozen", () => {
    const projets = [{ nom: "a", etat: enCodage(T0) }];
    // Le run était déjà silencieux : la visite est finie quand il passe « figé ? » (> 180 s).
    const { memoire, departs } = rejouer(projets, T0 + TICK, T0 + 185_000);

    expect(departs).toEqual(["a@" + (T0 + 35_000), "a@" + (T0 + 185_000)]);
    expect(memoire.visite?.projet).toBe("a");
  });

  it("goes to the agent the user chose, even during the delay between visits", () => {
    const projets = [
      { nom: "a", etat: enCodage(T0) },
      { nom: "b", etat: enCodage(T0 + 30_000) },
    ];
    // A passe silencieux à +35 s : la visite de santé est consommée, l'écart court.
    const apres = rejouer(projets, T0 + TICK, T0 + 60_000);
    expect(apres.memoire.visite).toBeNull();

    const demande = { projet: "b", poste: "codeur", a: T0 + 61_000 } as const;
    const choisi = ronde(apres.memoire, projets, demande, T0 + 65_000);

    expect(65_000 - 35_000).toBeLessThan(ECART_ENTRE_VISITES_MS);
    expect(choisi.visite).toEqual({ projet: "b", poste: "codeur", depuis: T0 + 65_000 });
  });

  it("lets a chosen agent replace a visit in progress, and leaves once for one choice", () => {
    const projets = [
      { nom: "a", etat: enCodage(T0) },
      { nom: "b", etat: enCodage(T0 + 30_000) },
    ];
    const enVisite = rejouer(projets, T0 + TICK, T0 + 35_000);
    expect(enVisite.memoire.visite?.projet).toBe("a");

    const demande = { projet: "b", poste: "codeur", a: T0 + 36_000 } as const;
    const chez = rejouer(projets, T0 + 40_000, T0 + 40_000 + DUREE_DE_VISITE_MS, demande, enVisite.memoire);
    expect(chez.departs).toEqual(["b@" + (T0 + 40_000)]);
    // La demande est traitée : au tick suivant la visite finie ne repart pas.
    expect(chez.memoire.visite).toBeNull();
  });

  it("makes only one visit for two silent runs while the delay has not passed", () => {
    // B passe silencieux à +55 s, vingt secondes après la visite de A.
    const projets = [
      { nom: "a", etat: enCodage(T0) },
      { nom: "b", etat: enCodage(T0 + 20_000) },
    ];
    const { departs } = rejouer(projets, T0 + TICK, T0 + 35_000 + ECART_ENTRE_VISITES_MS - TICK);

    expect(departs).toEqual(["a@" + (T0 + 35_000)]);
  });

  it("visits a second silent run once the delay has passed", () => {
    const projets = [
      { nom: "a", etat: enCodage(T0) },
      { nom: "b", etat: enCodage(T0 + 70_000) },
    ];
    const { departs } = rejouer(projets, T0 + TICK, T0 + 110_000);

    expect(departs).toEqual(["a@" + (T0 + 35_000), "b@" + (T0 + 105_000)]);
  });

  it("keeps him at his desk while a question waits, and ends a visit in progress", () => {
    const silencieux = [{ nom: "a", etat: enCodage(T0) }];
    const enVisite = rejouer(silencieux, T0 + TICK, T0 + 35_000);
    expect(enVisite.memoire.visite).not.toBeNull();

    const avecQuestion = [...silencieux, { nom: "b", etat: enQuestion(T0 + 36_000) }];
    const retenu = ronde(enVisite.memoire, avecQuestion, null, T0 + 40_000);
    expect(retenu.visite).toBeNull();

    const demande = { projet: "a", poste: "codeur", a: T0 + 41_000 } as const;
    expect(ronde(retenu, avecQuestion, demande, T0 + 45_000).visite).toBeNull();
  });

  it("does not leave for a choice made during a question once the question is answered", () => {
    const avecQuestion = [{ nom: "a", etat: enCodage(T0 + 100_000) }, { nom: "b", etat: enQuestion(T0 + 100_000) }];
    const demande = { projet: "a", poste: "codeur", a: T0 + 101_000 } as const;
    const retenu = ronde(MEMOIRE_VIERGE, avecQuestion, demande, T0 + 105_000);

    const sansQuestion = [{ nom: "a", etat: enCodage(T0 + 100_000) }, { nom: "b", etat: enCodage(T0 + 100_000) }];
    expect(ronde(retenu, sansQuestion, demande, T0 + 110_000).visite).toBeNull();
  });

  it("has nowhere to go for a run without a busy agent or a closed run", () => {
    const projets = [{ nom: "a", etat: clos(T0) }];
    const { departs } = rejouer(projets, T0 + TICK, T0 + 60_000);

    expect(departs).toEqual([]);
  });

  it("drops a visit whose room is gone", () => {
    const projets = [{ nom: "a", etat: enCodage(T0) }];
    const enVisite = rejouer(projets, T0 + TICK, T0 + 35_000);

    expect(ronde(enVisite.memoire, [], null, T0 + 40_000).visite).toBeNull();
  });

  it("returns the same memory when nothing changes, so a render can read it again", () => {
    const projets = [{ nom: "a", etat: enCodage(T0) }];
    const { memoire } = rejouer(projets, T0 + TICK, T0 + 35_000);

    expect(ronde(memoire, projets, null, T0 + 35_000)).toBe(memoire);
  });
});
