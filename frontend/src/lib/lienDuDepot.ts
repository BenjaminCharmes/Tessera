/**
 * L'URL navigable du dépôt d'un projet — ticket-184.
 *
 * Deux valeurs décrivent le même dépôt sans avoir la même forme :
 * `github_remote` d'`agents.json` vaut `owner/repo` — c'est ce que
 * `GitHubService` concatène dans `/repos/{repo}/issues` — tandis que
 * `remote_url` vient de git et porte une vraie adresse, en HTTPS ou en SSH.
 *
 * Les afficher toutes deux comme un lien demandait la même conversion à deux
 * endroits : elle n'est écrite qu'ici (ADR-034).
 */

/** Un segment de `owner/repo` : jamais vide, et jamais fait de seuls points. */
const SEGMENT = /^[\w.-]*[\w-][\w.-]*$/;

/** `git@hôte:owner/repo(.git)`, la forme SSH scp-like que git accepte. */
const SSH = /^(?:[\w.-]+@)?([\w.-]+):(.+)$/;

/**
 * Rend l'URL à ouvrir, ou `null` si la valeur ne permet pas de conclure.
 *
 * Un `null` vaut mieux qu'une supposition : un lien qui mène ailleurs coûte
 * plus qu'une adresse restée en texte.
 */
export function lienDuDepot(remote: string | null | undefined): string | null {
  const valeur = (remote ?? "").trim();
  if (valeur.length === 0) return null;

  if (estOwnerRepo(valeur)) {
    // Aucun hôte n'est déclaré dans cette forme : GitHub est le seul que le
    // produit sache interroger, donc le seul qu'on puisse supposer.
    return `https://github.com/${sansSuffixeGit(valeur)}`;
  }

  if (valeur.startsWith("https://") || valeur.startsWith("http://")) {
    return sansSuffixeGit(valeur);
  }

  const ssh = SSH.exec(valeur);
  if (ssh) {
    const [, hote, chemin] = ssh;
    return `https://${hote}/${sansSuffixeGit(chemin.replace(/^\/+/, ""))}`;
  }

  return null;
}

/**
 * Vrai pour `owner/repo`, faux pour un chemin.
 *
 * `..` s'écrit avec les mêmes caractères qu'un nom de dépôt : sans exiger un
 * caractère de mot par segment, `../voisin` devenait une URL GitHub.
 */
function estOwnerRepo(valeur: string): boolean {
  const segments = valeur.split("/");
  return segments.length === 2 && segments.every((s) => SEGMENT.test(s));
}

/** `.git` est une convention de clone, jamais une page qui s'ouvre. */
function sansSuffixeGit(valeur: string): string {
  return valeur.replace(/\.git$/, "");
}
