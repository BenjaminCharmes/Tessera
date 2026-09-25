/**
 * Une duree, telle qu'on la lit sur une carte de run — ticket-129.
 *
 * Dans son propre module : `Chrono` est un composant, et un fichier qui
 * exporte a la fois un composant et une fonction casse le rafraichissement a
 * chaud de Vite (`react-refresh/only-export-components`).
 */
export function formater(millisecondes: number): string {
  // Une date invalide donnerait « NaNs » a l'ecran : mieux vaut ne rien
  // pretendre que de pretendre faux.
  if (!Number.isFinite(millisecondes) || millisecondes < 0) return "—";
  const total = Math.floor(millisecondes / 1000);
  const heures = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secondes = total % 60;
  if (heures > 0) return `${heures}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secondes}s`;
  return `${secondes}s`;
}
