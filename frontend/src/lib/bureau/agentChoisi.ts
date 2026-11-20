import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent, RunActif } from "../../types/api";
import { LIBELLE_SANTE, santeAgent } from "../santeAgent";
import { nomDuPoste } from "./libelleDuPoste";
import { estTourDePlan } from "./plan";
import type { PosteId } from "./postesDuRun";
import { postesDuRun, transitionDe } from "./postesDuRun";

/** Une ligne du panneau « Agent choisi » : un libellé et ce que l'état en dit. */
export interface LigneDeLAgent {
  libelle: string;
  valeur: string;
}

/** Le temps écoulé en mots courts : « 12 s », « 3 min ». */
function ecoule(ms: number): string {
  const secondes = Math.max(0, Math.round(ms / 1000));
  return secondes < 60 ? `${secondes} s` : `${Math.floor(secondes / 60)} min`;
}

function ligneDuTicket(etat: StreamState, run?: RunActif): LigneDeLAgent | null {
  const id = etat.ticketId ?? run?.ticket_id ?? null;
  if (!id) return null;
  const titre = etat.ticketTitre ?? run?.ticket_titre ?? null;
  return { libelle: "Ticket", valeur: titre ? `${id} — ${titre}` : id };
}

function ligneDuTour(etat: StreamState): LigneDeLAgent | null {
  if (etat.currentRound <= 0) return null;
  const sur = etat.maxRounds ? ` / ${etat.maxRounds}` : "";
  return { libelle: "Tour", valeur: `${etat.currentRound}${sur}` };
}

function ligneDuSigne(etat: StreamState, maintenant: number): LigneDeLAgent | null {
  if (!etat.dernierEvenementA) return null;
  const depuis = maintenant - Date.parse(etat.dernierEvenementA);
  if (Number.isNaN(depuis)) return null;
  return { libelle: "Dernier signe de vie", valeur: `il y a ${ecoule(depuis)}` };
}

function ligneDeLAction(etat: StreamState, maintenant: number): LigneDeLAgent {
  const sante = santeAgent(
    etat.dernierEvenementA,
    maintenant,
    etat.pendingQuestion,
    etat.attenteExterieure !== null,
  );
  const question = etat.pendingQuestion ? ` : ${etat.pendingQuestion}` : "";
  return { libelle: "Il fait", valeur: `${LIBELLE_SANTE[sante]}${question}` };
}

/** La dernière fin d'étape de ce poste, hors plan rendu (le plan n'est pas le travail fini). */
function derniereFin(etat: StreamState, poste: PosteId): OrchestratorEvent | null {
  for (let i = etat.ticketEvents.length - 1; i >= 0; i--) {
    const ev = etat.ticketEvents[i];
    const t = transitionDe(ev);
    if (t?.poste === poste && t.transition === "fin" && !estTourDePlan(ev)) return ev;
  }
  return null;
}

/** Ce que l'étape a rendu, d'après son événement de fin ; null quand il ne le dit pas. */
function rendu(poste: PosteId, ev: OrchestratorEvent): string | null {
  const data = ev.data;
  switch (poste) {
    case "codeur":
      return "son code";
    case "testeur":
      return data["passed"] === true ? "tests verts" : data["passed"] === false ? "tests rouges" : null;
    case "securite":
      return typeof data["verdict"] === "string" ? `audit ${data["verdict"]}` : null;
    case "reviewer":
      if (data["verdict"] === "APPROVED") return "approuvé";
      return data["verdict"] === "CHANGES_REQUESTED" ? "changements demandés" : null;
    case "validateur":
      return data["approved"] === true ? "critères validés" : data["approved"] === false ? "critères refusés" : null;
  }
}

/** Un agent qui a fini : ce qu'il a rendu, et depuis quand (ticket-778). */
function lignesDeLaFin(etat: StreamState, poste: PosteId, maintenant: number): (LigneDeLAgent | null)[] {
  const fin = derniereFin(etat, poste);
  if (!fin) return [];
  const resultat = rendu(poste, fin);
  const depuis = maintenant - Date.parse(fin.timestamp);
  return [
    resultat ? { libelle: "A rendu", valeur: resultat } : null,
    Number.isNaN(depuis) ? null : { libelle: "Fini", valeur: `il y a ${ecoule(depuis)}` },
  ];
}

/** Un agent qui attend son tour : qui travaille avant lui, s'il y a quelqu'un (ticket-778). */
function ligneDeLAttente(etat: StreamState): LigneDeLAgent | null {
  const auTravail = postesDuRun(etat).find((p) => p.etat === "occupe");
  if (!auTravail) return null;
  return { libelle: "Il attend", valeur: `la fin de ${nomDuPoste(auTravail.poste)}` };
}

/**
 * Ce que l'état du run dit d'un agent, ligne par ligne, selon que son poste
 * travaille, a fini ou attend son tour. Une donnée absente fait disparaître sa
 * ligne (ADR-058) : le modèle, que ni `StreamState` ni les événements ne portent,
 * n'a donc pas de ligne. Un poste inconnu n'a rien à dire : `null`.
 */
export function lignesDeLAgent(
  projet: string,
  poste: PosteId,
  etat: StreamState,
  maintenant: number,
  run?: RunActif,
): LigneDeLAgent[] | null {
  const courant = postesDuRun(etat).find((p) => p.poste === poste);
  if (!courant) return null;
  const selonLEtat: (LigneDeLAgent | null)[] =
    courant.etat === "occupe"
      ? [ligneDuTour(etat), ligneDuSigne(etat, maintenant), ligneDeLAction(etat, maintenant)]
      : courant.etat === "fait"
        ? lignesDeLaFin(etat, poste, maintenant)
        : [ligneDeLAttente(etat)];
  const lignes: (LigneDeLAgent | null)[] = [
    { libelle: "Rôle", valeur: nomDuPoste(poste) },
    { libelle: "Projet", valeur: projet },
    ligneDuTicket(etat, run),
    ...selonLEtat,
  ];
  return lignes.filter((l): l is LigneDeLAgent => l !== null);
}
