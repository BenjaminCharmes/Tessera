import { useState } from "react";
import type { DayMoment } from "../lib/bureau/dayMoment";
import { lumiereAllumee } from "../lib/bureau/lumiere";
import type { Bascule } from "../lib/bureau/lumiere";

const PREFIXE = "tessera.bureau.lumiere.";

function lire(cle: string): Bascule | null {
  try {
    const brut = window.localStorage.getItem(PREFIXE + cle);
    if (brut === null) return null;
    const valeur: unknown = JSON.parse(brut);
    if (typeof valeur !== "object" || valeur === null) return null;
    const moment: unknown = Reflect.get(valeur, "moment");
    const allume: unknown = Reflect.get(valeur, "allume");
    if ((moment !== "jour" && moment !== "nuit") || typeof allume !== "boolean") return null;
    return { moment, allume };
  } catch {
    return null;
  }
}

function ecrire(cle: string, bascule: Bascule): void {
  try {
    window.localStorage.setItem(PREFIXE + cle, JSON.stringify(bascule));
  } catch {
    // Stockage indisponible : la bascule vaut pour la vie de la page.
  }
}

/**
 * La lumière d'une salle : allumée la nuit, éteinte le jour, sauf si l'interrupteur
 * l'a basculée pendant ce moment de la journée. Une préférence d'affichage, gardée
 * dans le navigateur de celui qui regarde.
 */
export function useLumiere(cle: string, moment: DayMoment): [boolean, () => void] {
  const [bascule, setBascule] = useState<Bascule | null>(() => lire(cle));
  const allume = lumiereAllumee(moment, bascule);
  function basculer() {
    const suivante: Bascule = { moment, allume: !allume };
    setBascule(suivante);
    ecrire(cle, suivante);
  }
  return [allume, basculer];
}
