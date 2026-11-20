import type { RythmeRituel } from "../../lib/apiRituels";

const heure = (h: string): string => h.slice(0, 5);

/** « Chaque lundi à 09:00 », « Le 5 du mois à 09:00 »… */
export function libelleDuRythme(r: RythmeRituel): string {
  if (r.type === "hebdo") return `Chaque ${r.jour} à ${heure(r.heure)}`;
  if (r.type === "mensuel") return `Le ${r.jour} du mois à ${heure(r.heure)}`;
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
