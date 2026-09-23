/**
 * L'adresse qu'un service annonce dans sa sortie — ticket-145.
 *
 * Vite écrit « Local: http://localhost:5174/ », uvicorn « Uvicorn running on
 * http://127.0.0.1:8000 ». Sans cette lecture, on lance un serveur sans
 * savoir où il écoute — c'est le premier reproche fait au bouton.
 *
 * C'est une **heuristique** : elle ne remplace rien, la sortie reste lisible
 * en entier. Mieux vaut n'afficher aucun lien qu'un lien mort.
 */
const ADRESSE = /https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?\/?\S*/;

export function adresseDansLaSortie(lignes: string[]): string | null {
  // La dernière l'emporte : un serveur qui redémarre sur un autre port
  // annonce le nouveau, et c'est celui-là qui est vivant.
  for (const ligne of [...lignes].reverse()) {
    const trouve = ADRESSE.exec(ligne);
    if (trouve) return trouve[0].replace(/[.,;)]+$/, "");
  }
  return null;
}
