/**
 * L'en-tête YAML d'un Markdown, séparé de son corps — ticket-334.
 *
 * `marked` ne connaît pas le frontmatter : le `---` d'ouverture devenait une
 * règle horizontale, les champs un seul paragraphe, et le `---` de fermeture
 * un titre. Les tickets en ont tous un.
 *
 * Ce n'est pas un parseur YAML : un champ par ligne `clé: valeur`, une ligne
 * indentée prolonge la valeur précédente (titre replié par le sérialiseur).
 * C'est tout ce qu'écrivent les tickets, et l'affichage seul en dépend.
 */

export interface Separation {
  /** `null` quand le fichier n'ouvre pas sur un en-tête. */
  champs: [string, string][] | null;
  corps: string;
}

const EN_TETE = /^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;
const CHAMP = /^([A-Za-z_][\w-]*):[ \t]*(.*)$/;

function sansGuillemets(valeur: string): string {
  const v = valeur.trim();
  const entoure = v.length >= 2 && (v[0] === '"' || v[0] === "'") && v.at(-1) === v[0];
  return entoure ? v.slice(1, -1) : v;
}

export function separerFrontmatter(source: string): Separation {
  const trouve = EN_TETE.exec(source);
  if (!trouve) return { champs: null, corps: source };

  const champs: [string, string][] = [];
  for (const ligne of trouve[1].split(/\r?\n/)) {
    const champ = CHAMP.exec(ligne);
    if (champ) {
      champs.push([champ[1], champ[2]]);
    } else if (/^\s+\S/.test(ligne) && champs.length > 0) {
      const dernier = champs[champs.length - 1];
      dernier[1] = `${dernier[1]} ${ligne.trim()}`.trim();
    }
  }
  return {
    champs: champs.map(([cle, valeur]) => [cle, sansGuillemets(valeur)]),
    corps: source.slice(trouve[0].length),
  };
}
