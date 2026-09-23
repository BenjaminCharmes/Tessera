/**
 * Les adresses qu'un service annonce dans sa sortie — ticket-145, ticket-154.
 *
 * Vite écrit « Local: http://localhost:5174/ », uvicorn « Uvicorn running on
 * http://127.0.0.1:8000 ». Sans cette lecture, on lance un serveur sans
 * savoir où il écoute — c'est le premier reproche fait au bouton.
 *
 * C'est une **heuristique** : elle ne remplace rien, la sortie reste lisible
 * en entier. Mieux vaut n'afficher aucun lien qu'un lien mort.
 */

/** Une adresse, et le service qui l'a annoncée quand la sortie le préfixe. */
export interface AdresseAnnoncee {
  url: string;
  /** Le `[web]` / `[server]` de `concurrently`, sans les crochets. */
  etiquette: string | null;
}

//: Le chemin s'arrête au premier caractère qui n'a rien à faire dans une URL.
//: `\S*` avalait le `"}` fermant d'un log JSON, et le lien corrompu tombait
//: sur about:blank#blocked (ticket-154).
const ADRESSE =
  /https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:\/[^\s"'`<>{}|\\]*)?/;

//: `concurrently -n server,web` préfixe chaque ligne. C'est le seul indice
//: qui distingue deux serveurs lancés par une commande unique.
const ETIQUETTE = /^\s*\[([^\]\s]+)\]\s?/;

/** Le port d'une URL, 80 ou 443 par défaut. */
function port(url: string): string {
  const explicite = /:(\d+)(?:\/|$)/.exec(url.replace(/^https?:\/\//, ""));
  if (explicite) return explicite[1];
  return url.startsWith("https://") ? "443" : "80";
}

export function adressesDansLaSortie(
  lignes: string[],
  origineDeLIde: string,
): AdresseAnnoncee[] {
  // Le port suffit : les trois écritures d'hôte local désignent la même
  // machine, et un service ne peut pas écouter là où le frontend de Tessera
  // écoute déjà. Vite le dit lui-même en changeant de port (ticket-154).
  const portDeLIde = port(origineDeLIde);

  // Par étiquette, la dernière l'emporte — un serveur qui redémarre sur un
  // autre port annonce le nouveau, et c'est celui-là qui est vivant. Une Map
  // garde l'ordre de première apparition, donc `[web]` reste avant `[server]`.
  const parEtiquette = new Map<string, AdresseAnnoncee>();

  for (const ligne of lignes) {
    const prefixe = ETIQUETTE.exec(ligne);
    const etiquette = prefixe ? prefixe[1] : null;
    const trouve = ADRESSE.exec(prefixe ? ligne.slice(prefixe[0].length) : ligne);
    if (!trouve) continue;

    const url = trouve[0].replace(/[.,;)]+$/, "");
    if (port(url) === portDeLIde) continue;

    parEtiquette.set(etiquette ?? "", { url, etiquette });
  }

  return [...parEtiquette.values()];
}
