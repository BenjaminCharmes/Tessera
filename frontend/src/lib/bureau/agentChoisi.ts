import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";
import { LIBELLE_SANTE, santeAgent } from "../santeAgent";
import { nomDuPoste } from "./libelleDuPoste";
import type { PosteId } from "./postesDuRun";
import { postesDuRun } from "./postesDuRun";

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

/**
 * Ce que l'état du run dit d'un agent au travail, ligne par ligne. Une donnée
 * absente fait disparaître sa ligne (ADR-058) : le modèle, que ni `StreamState`
 * ni les événements ne portent, n'a donc pas de ligne. Un poste qui n'est pas
 * `occupe` n'a rien à dire : `null`.
 */
export function lignesDeLAgent(
  projet: string,
  poste: PosteId,
  etat: StreamState,
  maintenant: number,
  run?: RunActif,
): LigneDeLAgent[] | null {
  const courant = postesDuRun(etat).find((p) => p.poste === poste);
  if (courant?.etat !== "occupe") return null;
  const lignes: (LigneDeLAgent | null)[] = [
    { libelle: "Rôle", valeur: nomDuPoste(poste) },
    { libelle: "Projet", valeur: projet },
    ligneDuTicket(etat, run),
    ligneDuTour(etat),
    ligneDuSigne(etat, maintenant),
    ligneDeLAction(etat, maintenant),
  ];
  return lignes.filter((l): l is LigneDeLAgent => l !== null);
}
