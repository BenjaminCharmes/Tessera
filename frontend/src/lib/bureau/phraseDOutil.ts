/** Longueur maximale d'une phrase de bulle, points de suspension compris (ticket-601). */
export const LONGUEUR_MAX_DE_LA_PHRASE = 32;

/** Les lanceurs derrière lesquels se cache la vraie commande : `uv run pytest`, `npx vitest`. */
const LANCEURS: readonly (readonly string[])[] = [["uv", "run"], ["npm", "run"], ["npx"]];

const OUTILS_DE_LECTURE: readonly string[] = ["Read", "NotebookRead"];
const OUTILS_D_EDITION: readonly string[] = ["Edit", "Write", "MultiEdit"];
const OUTILS_DE_RECHERCHE: readonly string[] = ["Grep", "Glob"];

function texte(entree: Record<string, unknown>, cles: readonly string[]): string | null {
  for (const cle of cles) {
    const valeur = entree[cle];
    if (typeof valeur === "string" && valeur.trim() !== "") return valeur.trim();
  }
  return null;
}

/** Le dernier élément d'un chemin, séparateur Windows ou POSIX : jamais le dossier. */
function nomDeFichier(chemin: string): string {
  const morceaux = chemin.split(/[\\/]/).filter((m) => m !== "");
  return morceaux[morceaux.length - 1] ?? chemin;
}

/** Le premier segment d'une ligne de commande qui ne se contente pas de changer de dossier. */
function segmentUtile(commande: string): string {
  const segments = commande.split(/&&|;|\|\|/).map((s) => s.trim());
  return segments.find((s) => s !== "" && !/^cd(\s|$)/.test(s)) ?? "";
}

/** Retire les lanceurs en tête, puis les options : ce qui reste commence par le vrai programme. */
function motsDeLaCommande(segment: string): string[] {
  let mots = segment.split(/\s+/).filter((m) => m !== "");
  const lanceur = LANCEURS.find((l) => l.every((mot, i) => mots[i] === mot));
  if (lanceur) mots = mots.slice(lanceur.length);
  return mots.filter((m) => !m.startsWith("-"));
}

function phraseDeCommande(entree: Record<string, unknown>): string {
  const commande = texte(entree, ["command"]);
  const premier = commande === null ? undefined : motsDeLaCommande(segmentUtile(commande))[0];
  return premier === undefined ? "lance une commande" : `lance ${nomDeFichier(premier)}`;
}

/** Coupe au-delà de 32 caractères, « … » compris. */
export function tronquer(phrase: string): string {
  if (phrase.length <= LONGUEUR_MAX_DE_LA_PHRASE) return phrase;
  return `${phrase.slice(0, LONGUEUR_MAX_DE_LA_PHRASE - 1)}…`;
}

function phraseBrute(outil: string, entree: Record<string, unknown>): string {
  const repli = `utilise ${outil}`;
  if (OUTILS_DE_LECTURE.includes(outil) || OUTILS_D_EDITION.includes(outil)) {
    const chemin = texte(entree, ["file_path", "notebook_path", "path"]);
    if (chemin === null) return repli;
    return `${OUTILS_DE_LECTURE.includes(outil) ? "lit" : "édite"} ${nomDeFichier(chemin)}`;
  }
  if (outil === "Bash") return phraseDeCommande(entree);
  if (OUTILS_DE_RECHERCHE.includes(outil)) {
    const motif = texte(entree, ["pattern"]);
    return motif === null ? repli : `cherche "${motif}"`;
  }
  return repli;
}

/**
 * Ce que l'agent fait, en une ligne pour la bulle de son poste.
 *
 * Seul le nom du fichier est dit, jamais son chemin : la bulle est lue par
 * quiconque regarde l'écran, et un chemin complet porte le dossier de la machine.
 */
export function phraseDOutil(outil: string, entree: Record<string, unknown>): string {
  return tronquer(phraseBrute(outil, entree));
}
