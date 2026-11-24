import type { Interruption, RythmeRituel } from "../../lib/apiRituels";

const heure = (h: string): string => h.slice(0, 5);

/** « Chaque lundi à 09:00 », « Le 5 du mois à 09:00 »… */
export function libelleDuRythme(r: RythmeRituel): string {
  if (r.type === "hebdo") return `Chaque ${r.jour} à ${heure(r.heure)}`;
  if (r.type === "mensuel") return `Le ${r.jour} du mois à ${heure(r.heure)}`;
  if (r.type === "quotidien") {
    return `Chaque jour${r.jours === "ouvres" ? " ouvré" : ""} à ${heure(r.heure)}`;
  }
  return `Du ${r.du} au ${r.au}`;
}

/** Une date lisible en français ; un tiret quand la date manque. */
export function libelleDeDate(iso: string | null): string {
  if (iso === null) return "—";
  return new Date(iso).toLocaleString("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * « en retard de 9 h » : minutes sous une heure, heures sous une journée, jours
 * au-delà — l'échéance n'a pas plus de précision que cela.
 */
export function libelleDuRetard(derniere: string | null, maintenant: Date): string | null {
  if (derniere === null) return null;
  const minutes = Math.max(0, Math.floor((maintenant.getTime() - new Date(derniere).getTime()) / 60000));
  if (minutes < 60) return `en retard de ${minutes} min`;
  if (minutes < 24 * 60) return `en retard de ${Math.floor(minutes / 60)} h`;
  return `en retard de ${Math.floor(minutes / (24 * 60))} j`;
}

/** L'interruption qui couvre l'échéance, s'il y en a une. */
export function interruptionDe(derniere: string | null, liste: Interruption[]): Interruption | undefined {
  if (derniere === null) return undefined;
  const t = new Date(derniere).getTime();
  return liste.find((i) => new Date(i.debut).getTime() <= t && t <= new Date(i.fin).getTime());
}
