import type { StreamState } from "../../hooks/streamState";
import { indiceDuDernier } from "./fete";

/** L'état d'une ligne du tableau blanc : pas encore jugée, validée, ou refusée. */
export type EtatCase = "attente" | "passe" | "echoue";

export interface LigneDuTableau {
  /** Le texte du critère ; vide quand ni le verdict ni le fichier du ticket ne le donnent. */
  texte: string;
  etat: EtatCase;
}

export interface TableauDesCriteres {
  lignes: LigneDuTableau[];
  valides: number;
}

const ENTETE_DES_CRITERES = /^#{1,6}\s*(?:crit[èe]res d['’]acceptation|acceptance criteria)\b/i;
const ENTETE_QUELCONQUE = /^#{1,6}\s/;
const CASE_A_COCHER = /^\s*[-*]\s*\[[ xX]\]\s*(.*)$/;

/**
 * Les critères d'un ticket, lus dans la section « Critères d'acceptation » de
 * son fichier : une ligne à cocher par critère, jusqu'à l'en-tête suivant.
 * Une section absente ou sans ligne à cocher ne dit rien : liste vide.
 */
export function criteresDuCorps(corps: string): string[] {
  const criteres: string[] = [];
  let dansLaSection = false;
  for (const ligne of corps.split(/\r?\n/)) {
    if (ENTETE_DES_CRITERES.test(ligne)) {
      dansLaSection = true;
    } else if (ENTETE_QUELCONQUE.test(ligne)) {
      dansLaSection = false;
    } else if (dansLaSection) {
      const texte = CASE_A_COCHER.exec(ligne)?.[1];
      if (texte !== undefined) criteres.push(texte.trim());
    }
  }
  return criteres;
}

/**
 * Le ticket dont la pièce joue le run : celui du dernier événement qui en porte un
 * (un run à un seul ticket ne pose pas `ticketId`), sinon celui de l'état.
 */
export function ticketDuRun(etat: StreamState): string | null {
  const dernier = etat.ticketEvents.findLast((ev) => Boolean(ev.ticket_id));
  return dernier?.ticket_id || etat.ticketId;
}

export interface CritereJuge {
  criterion: string;
  passed: boolean;
}

function critereJuge(brut: unknown): CritereJuge | null {
  if (typeof brut !== "object" || brut === null) return null;
  const critere: unknown = Reflect.get(brut, "criterion");
  const passe: unknown = Reflect.get(brut, "passed");
  return { criterion: typeof critere === "string" ? critere : "", passed: passe === true };
}

/**
 * Les critères du dernier `validation_done` du ticket, ou `null` : aucun verdict,
 * un tour de validation reparti depuis (le tableau se vide), ou un verdict sans critère.
 */
export function criteresJuges(etat: StreamState): CritereJuge[] | null {
  const evenements = etat.ticketEvents;
  const fini = indiceDuDernier(evenements, "validation_done");
  if (fini < 0 || indiceDuDernier(evenements, "validation_started") > fini) return null;
  const brut: unknown = evenements[fini]?.data["criteria"];
  if (!Array.isArray(brut)) return null;
  const juges = brut.map(critereJuge).filter((c): c is CritereJuge => c !== null);
  return juges.length > 0 ? juges : null;
}

/**
 * Le tableau : les critères jugés s'ils le sont, sinon une ligne grise par critère
 * du fichier du ticket, sinon rien (ADR-058 : on ne dessine que ce qu'on sait).
 */
export function tableauDesCriteres(juges: CritereJuge[] | null, attendus: readonly string[]): TableauDesCriteres {
  if (juges !== null) {
    const lignes = juges.map((c): LigneDuTableau => ({ texte: c.criterion, etat: c.passed ? "passe" : "echoue" }));
    return { lignes, valides: juges.filter((c) => c.passed).length };
  }
  return { lignes: attendus.map((texte): LigneDuTableau => ({ texte, etat: "attente" })), valides: 0 };
}

/** « Tableau blanc : 4 critères sur 5 validés » ; sans critère connu, il le dit. */
export function libelleDuTableau({ lignes, valides }: TableauDesCriteres): string {
  if (lignes.length === 0) return "Tableau blanc : aucun critère connu";
  return `Tableau blanc : ${valides} ${valides > 1 ? "critères" : "critère"} sur ${lignes.length} validés`;
}

const ETAT_DITS: Record<EtatCase, string> = {
  attente: "pas encore jugé",
  passe: "validé",
  echoue: "refusé",
};

/** L'état d'une ligne, en toutes lettres. */
export function etatDit(etat: EtatCase): string {
  return ETAT_DITS[etat];
}

/** Une ligne de l'infobulle : le critère et son état, en toutes lettres. */
export function ligneDeLInfobulle({ texte, etat }: LigneDuTableau, rang: number): string {
  return `${texte || `Critère ${rang + 1}`} — ${ETAT_DITS[etat]}`;
}
