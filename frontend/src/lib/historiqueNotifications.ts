import { ecrireEtatPersistant, lireEtatPersistant } from "../hooks/useEtatPersistant";
import { TYPES_NOTIF, type Notif } from "./notifications";

/**
 * L'historique du jour de la cloche — ticket-554.
 *
 * Toute notification produite y entre, qu'elle parte vers le système ou non.
 * Il ne vit que dans le navigateur et ne passe pas minuit : le premier
 * chargement ou la première entrée d'un nouveau jour le vide. Fonctions pures,
 * l'horloge est injectée ; seuls `lireHistorique` et `ecrireHistorique` touchent
 * au stockage.
 */
export interface EntreeHistorique extends Notif {
  id: string;
  /** Horodatage de la production, en millisecondes. */
  a: number;
  lu: boolean;
}

export interface Historique {
  /** Le jour local, `AAAA-MM-JJ`. */
  jour: string;
  /** Du plus récent au plus ancien. */
  items: EntreeHistorique[];
}

const CLE = "notifications.historique";
const PLAFOND = 200;

export function jourLocal(date: Date): string {
  const deux = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${deux(date.getMonth() + 1)}-${deux(date.getDate())}`;
}

export function historiqueVide(date: Date): Historique {
  return { jour: jourLocal(date), items: [] };
}

/** Un historique d'un autre jour repart à vide ; celui du jour reste tel quel. */
export function purgerSiAutreJour(h: Historique, date: Date): Historique {
  return h.jour === jourLocal(date) ? h : historiqueVide(date);
}

export function ajouter(h: Historique, notifs: Notif[], date: Date): Historique {
  const courant = purgerSiAutreJour(h, date);
  const a = date.getTime();
  const nouvelles = notifs
    .map((n, i): EntreeHistorique => ({ ...n, id: `${a}-${courant.items.length}-${i}`, a, lu: false }))
    .reverse();
  return { ...courant, items: [...nouvelles, ...courant.items].slice(0, PLAFOND) };
}

export function toutMarquerLu(h: Historique): Historique {
  return { ...h, items: h.items.map((e) => (e.lu ? e : { ...e, lu: true })) };
}

export function nonLus(h: Historique): number {
  return h.items.filter((e) => !e.lu).length;
}

function estHistorique(v: unknown): v is Historique {
  if (typeof v !== "object" || v === null) return false;
  const { jour, items } = v as Record<string, unknown>;
  return typeof jour === "string" && Array.isArray(items) && items.every(estEntree);
}

function estEntree(v: unknown): v is EntreeHistorique {
  if (typeof v !== "object" || v === null) return false;
  const e = v as Record<string, unknown>;
  return (
    typeof e.id === "string" &&
    typeof e.a === "number" &&
    typeof e.lu === "boolean" &&
    typeof e.projectId === "string" &&
    typeof e.titre === "string" &&
    typeof e.corps === "string" &&
    (TYPES_NOTIF as readonly unknown[]).includes(e.type)
  );
}

/** Relit l'historique mémorisé, déjà purgé s'il date d'un autre jour. */
export function lireHistorique(date: Date): Historique {
  const memorise = lireEtatPersistant<Historique>(CLE, historiqueVide(date), estHistorique);
  return purgerSiAutreJour(memorise, date);
}

export function ecrireHistorique(h: Historique): void {
  ecrireEtatPersistant(CLE, h);
}
