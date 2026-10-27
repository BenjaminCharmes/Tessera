import type { DayMoment } from "./dayMoment";

/** Ce que l'interrupteur a choisi, et pendant quel moment de la journée. */
export interface Bascule {
  moment: DayMoment;
  allume: boolean;
}

/**
 * Allumée la nuit, éteinte le jour (ticket-602) ; une bascule de l'interrupteur
 * l'emporte tant que le moment de la journée n'a pas changé.
 */
export function lumiereAllumee(moment: DayMoment, bascule: Bascule | null): boolean {
  if (bascule !== null && bascule.moment === moment) return bascule.allume;
  return moment === "nuit";
}
