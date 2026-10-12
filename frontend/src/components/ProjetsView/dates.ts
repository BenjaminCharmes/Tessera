/**
 * Les dates d'une carte de projet — ticket-399.
 *
 * Le relatif (« il y a 2 j ») se lit d'un coup d'œil ; la date exacte reste en
 * info-bulle pour qui veut la vérifier.
 */
const MINUTE = 60_000;
const HEURE = 60 * MINUTE;
const JOUR = 24 * HEURE;

/** « il y a 2 j » ; chaîne vide si la date est absente ou illisible. */
export function ilYa(iso: string | null, maintenant: number = Date.now()): string {
  const t = iso ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(t)) return "";
  const ecart = Math.max(0, maintenant - t);
  if (ecart < MINUTE) return "à l'instant";
  if (ecart < HEURE) return `il y a ${Math.floor(ecart / MINUTE)} min`;
  if (ecart < JOUR) return `il y a ${Math.floor(ecart / HEURE)} h`;
  if (ecart < 30 * JOUR) return `il y a ${Math.floor(ecart / JOUR)} j`;
  if (ecart < 365 * JOUR) return `il y a ${Math.floor(ecart / (30 * JOUR))} mois`;
  const ans = Math.floor(ecart / (365 * JOUR));
  return `il y a ${ans} ${ans > 1 ? "ans" : "an"}`;
}

/** La date et l'heure exactes, pour l'info-bulle. */
export function dateExacte(iso: string | null): string {
  const t = iso ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(t)) return "";
  return new Date(t).toLocaleString("fr-FR", {
    dateStyle: "long",
    timeStyle: "short",
  });
}
