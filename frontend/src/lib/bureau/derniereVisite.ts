/** La clé de la date de dernière visite du récap du superviseur (ticket-861). */
export const CLE_DERNIERE_VISITE = "tessera.ui.supervision.derniereVisite";

const FORME_D_UN_JOUR = /^\d{4}-\d{2}-\d{2}$/;

/** Le jour de la dernière visite, ou `null` : jamais venu, valeur illisible, stockage fermé. */
export function lireDerniereVisite(): string | null {
  try {
    const valeur = window.localStorage.getItem(CLE_DERNIERE_VISITE);
    return valeur !== null && FORME_D_UN_JOUR.test(valeur) ? valeur : null;
  } catch {
    return null;
  }
}

/** Mémorise le jour (`AAAA-MM-JJ`) ; un stockage refusé ne casse rien. */
export function memoriserVisite(jour: string): void {
  try {
    window.localStorage.setItem(CLE_DERNIERE_VISITE, jour);
  } catch {
    // Stockage indisponible : le récap montrera simplement tout la prochaine fois.
  }
}

/** Le jour d'une date, au fuseau local. */
export function jourDe(date: Date): string {
  const deux = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${deux(date.getMonth() + 1)}-${deux(date.getDate())}`;
}
