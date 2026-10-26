import { TYPES_NOTIF, type TypeNotif } from "./notifications";

/**
 * Ce que chaque type d'événement fait, réglé depuis la cloche — ticket-554.
 *
 * « Système » : la notification sort de l'appli. « Son » : une alerte sonore
 * (le son lui-même vient avec le ticket-566 ; ici la case est seulement
 * mémorisée). L'interrupteur général des notifications système
 * (`CLE_REGLAGE`, ticket-193) reste au-dessus : coupé, rien ne part.
 */
export interface ReglageDuType {
  systeme: boolean;
  son: boolean;
}

export type ReglagesParType = Record<TypeNotif, ReglageDuType>;

export const CLE_REGLAGES_PAR_TYPE = "notifications.types";

export const LIBELLES_TYPE: Record<TypeNotif, string> = {
  question: "Question d'un agent",
  fige: "Agent figé",
  bloque: "Run bloqué",
  termine: "Run terminé",
  merge: "PR mergée",
  ci_rouge: "CI rouge ou merge refusé",
  quota_bas: "Quota bas",
};

const AVEC_SON: readonly TypeNotif[] = ["question", "ci_rouge"];

export function reglagesParDefaut(): ReglagesParType {
  const reglages = {} as ReglagesParType;
  for (const type of TYPES_NOTIF) {
    reglages[type] = { systeme: true, son: AVEC_SON.includes(type) };
  }
  return reglages;
}

function estReglageDuType(v: unknown): v is ReglageDuType {
  if (typeof v !== "object" || v === null) return false;
  const r = v as Record<string, unknown>;
  return typeof r.systeme === "boolean" && typeof r.son === "boolean";
}

/** Un réglage mémorisé auquel il manque un type ne vaut rien : les défauts servent. */
export function estReglagesParType(v: unknown): v is ReglagesParType {
  if (typeof v !== "object" || v === null) return false;
  const r = v as Record<string, unknown>;
  return TYPES_NOTIF.every((type) => estReglageDuType(r[type]));
}
