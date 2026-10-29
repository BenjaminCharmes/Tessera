import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import { prARelire } from "./aToi";
import type { ProjetPourLaColonne } from "./aToi";
import { boiteAuxLettres, surveilleeParLeWatcher } from "./boiteAuxLettres";

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

export interface OccupantDePause {
  projet: string;
  pause: Pause;
}

export interface OccupantDeReunion {
  projet: string;
  reunion: Reunion;
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
    return pause === null ? [] : [{ projet: nom, pause }];
  });
}

/** Les projets dont le run est en salle de réunion. */
export function occupantsDeLaReunion(projets: readonly ProjetPourLaColonne[]): OccupantDeReunion[] {
  return projets.flatMap(({ nom, etat }) => {
    const reunion = laReunion(etat);
    return reunion === null ? [] : [{ projet: nom, reunion }];
  });
}
