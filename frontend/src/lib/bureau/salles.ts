import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import { prARelire } from "./aToi";
import type { ProjetPourLaColonne } from "./aToi";
import { boiteAuxLettres, surveilleeParLeWatcher } from "./boiteAuxLettres";
import { postesDuRun } from "./postesDuRun";
import type { PosteId } from "./postesDuRun";

/** Ce qui met un run en salle de pause : ni du travail, ni un blocage. */
export interface Pause {
  motif: "quota" | "dependance" | "ci";
  libelle: string;
}

/**
 * Où en est un conflit confié au résolveur : ses fichiers pendant le travail,
 * puis la PR à relire (ADR-033). Une résolution annulée ne laisse rien.
 */
export type Reunion = { temps: "conflit"; fichiers: string[] } | { temps: "relecture"; pr: number };

/** Un agent en salle de pause ; `pr` : il tient la PR en main plutôt qu'une tasse. */
export interface PosteEnPause {
  poste: PosteId;
  pr: boolean;
}

/**
 * Qui vient en salle de pause, selon ce que le run attend (ticket-784) : le validateur
 * qui a approuvé la livraison, la PR en main, pendant la CI ; le codeur et le reviewer,
 * tasse en main, le temps que le quota revienne ; le codeur, devant la machine, tant
 * qu'une dépendance n'est pas mergée. Chacun vient d'un état du run (ADR-058).
 */
const POSTES_EN_PAUSE: Record<Pause["motif"], PosteEnPause[]> = {
  ci: [{ poste: "validateur", pr: true }],
  quota: [
    { poste: "codeur", pr: false },
    { poste: "reviewer", pr: false },
  ],
  dependance: [{ poste: "codeur", pr: false }],
};

export interface OccupantDePause {
  projet: string;
  pause: Pause;
  /** Les agents de la pause qui ont quitté leur bureau : pas ceux que le run courant occupe. */
  postes: PosteEnPause[];
}

export interface OccupantDeReunion {
  projet: string;
  reunion: Reunion;
  /** Les agents de la table qui ont quitté leur bureau (le reviewer, pendant un conflit). */
  postes: PosteId[];
}

/** Les postes que le run courant occupe : un agent au travail reste à son bureau. */
function postesOccupes(etat: StreamState): Set<PosteId> {
  return new Set(postesDuRun(etat).filter((p) => p.etat === "occupe").map((p) => p.poste));
}

/** Les agents d'une pause qui sont réellement en salle de pause, hors ceux que le run occupe. */
export function postesEnPause(etat: StreamState, pause: Pause): PosteEnPause[] {
  const occupes = postesOccupes(etat);
  return POSTES_EN_PAUSE[pause.motif].filter((p) => !occupes.has(p.poste));
}

/** Les agents d'une réunion qui sont réellement à la table : le reviewer pendant un conflit, s'il n'est pas au travail. */
export function postesEnReunion(etat: StreamState, reunion: Reunion): PosteId[] {
  if (reunion.temps !== "conflit") return [];
  return postesOccupes(etat).has("reviewer") ? [] : ["reviewer"];
}

const HEURE_INCONNUE = "heure inconnue";

/** Le `resume` du dernier `error` de quota épuisé parmi ces événements, ou null s'il n'y en a pas. */
function resumeDuDernierQuota(evenements: readonly OrchestratorEvent[]): string | null {
  for (let i = evenements.length - 1; i >= 0; i--) {
    const ev = evenements[i];
    if (ev.type !== "error" || ev.data["reason"] !== "quota_exhausted") continue;
    const resume = ev.data["resume"];
    return typeof resume === "string" && resume !== "" ? resume : HEURE_INCONNUE;
  }
  return null;
}

/**
 * Une file qui s'arrête sur quota annonce `queue_progress` avec `raison: "quota_exhausted"`
 * (orchestrator.py). Il n'est pas forcément le dernier : `run_closed` le suit toujours.
 * Un ticket suivant aurait ramené `ticketEvents` à son propre `queue_progress`,
 * donc celui d'arrêt, s'il y est, est bien celui du ticket courant.
 */
function fileArreteeSurQuota(etat: StreamState): boolean {
  return etat.ticketEvents.some(
    (ev) => ev.type === "queue_progress" && ev.data["raison"] === "quota_exhausted",
  );
}

/**
 * Le `resume` d'un run clos sur quota épuisé : il se relance à la main.
 *
 * Seul un run d'un ticket garde son `error` dans `ticketEvents`. En file, le
 * `queue_progress` d'arrêt remet `ticketEvents` à zéro : l'`error` ne survit
 * que dans `events`, qui garde l'historique du run.
 */
function quotaEpuise(etat: StreamState): string | null {
  const direct = resumeDuDernierQuota(etat.ticketEvents);
  if (direct !== null) return direct;
  return fileArreteeSurQuota(etat) ? (resumeDuDernierQuota(etat.events) ?? HEURE_INCONNUE) : null;
}

function numeroDePr(pr: number | null): string {
  return pr === null ? "d'une PR" : `de la PR #${pr}`;
}

/**
 * Les PR confiées au watcher dont la CI n'a pas rendu, lues dans toute la file.
 *
 * Le ticket suivant remet `ticketEvents` à zéro (ADR-051) : seule `events` garde
 * la livraison d'un ticket passé. Une PR est en CI tant qu'aucun `ci_merge_done`
 * ne porte son numéro.
 */
function prsEnCi(etat: StreamState): number[] {
  const terminees = new Set<number>();
  const enCi: number[] = [];
  for (const ev of etat.events) {
    const pr = ev.data["pr_number"];
    if (typeof pr !== "number") continue;
    if (ev.type === "ci_merge_done") terminees.add(pr);
    else if (ev.type === "livraison_done" && surveilleeParLeWatcher(ev)) enCi.push(pr);
  }
  return enCi.filter((pr) => !terminees.has(pr));
}

/** La pause du run, ou null : quota épuisé, dépendance attendue, ou CI de la phase 2. */
export function laPause(etat: StreamState): Pause | null {
  const resume = quotaEpuise(etat);
  if (resume !== null) return { motif: "quota", libelle: `Quota épuisé, reprise ${resume}` };
  const attente = etat.attenteExterieure;
  if (attente !== null && attente.raison === "dependency") {
    return { motif: "dependance", libelle: `Attend le merge ${numeroDePr(attente.pr)}` };
  }
  const boite = boiteAuxLettres(etat);
  if (boite.etat === "ci") return { motif: "ci", libelle: `CI en cours ${numeroDePr(boite.pr)}` };
  const enCi = prsEnCi(etat);
  if (enCi.length === 0) return null;
  return { motif: "ci", libelle: `CI en cours ${numeroDePr(enCi[enCi.length - 1])}` };
}

/** La réunion du run, ou null : conflit en cours, puis PR à relire. */
export function laReunion(etat: StreamState): Reunion | null {
  if (etat.conflitEnCours !== null) return { temps: "conflit", fichiers: etat.conflitEnCours };
  const pr = prARelire(etat);
  return pr === null ? null : { temps: "relecture", pr };
}

/** Les projets dont le run est en salle de pause. */
export function occupantsDeLaPause(projets: readonly ProjetPourLaColonne[]): OccupantDePause[] {
  return projets.flatMap(({ nom, etat }) => {
    const pause = laPause(etat);
    return pause === null ? [] : [{ projet: nom, pause, postes: postesEnPause(etat, pause) }];
  });
}

/** Les projets dont le run est en salle de réunion. */
export function occupantsDeLaReunion(projets: readonly ProjetPourLaColonne[]): OccupantDeReunion[] {
  return projets.flatMap(({ nom, etat }) => {
    const reunion = laReunion(etat);
    return reunion === null ? [] : [{ projet: nom, reunion, postes: postesEnReunion(etat, reunion) }];
  });
}
