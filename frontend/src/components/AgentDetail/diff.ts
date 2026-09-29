/**
 * Line-level diff between two texts — ticket-226.
 *
 * Used to show what would change in a prompt before confirming the save.
 * The algorithm is LCS-based: it produces the shortest edit sequence between
 * two texts split by newline.
 *
 * The LCS table weighs n × m cells. The common prefix and suffix are taken out
 * first, which leaves only the edited region for an ordinary prompt change;
 * past `CELLULES_MAX`, the region is shown as removed then added instead —
 * the security audit of ticket-226 blocked an unbounded table.
 */

export type TypeDeLigneDiff = "ajout" | "retrait" | "contexte";

export interface LigneDiff {
  type: TypeDeLigneDiff;
  texte: string;
}

/** Past this many cells, the edited region is not diffed line by line. */
const CELLULES_MAX = 1_000_000;

/**
 * Computes a line-level diff between two texts.
 * Returns typed lines: "ajout" (green), "retrait" (red), "contexte" (unchanged).
 */
export function diffLignes(avant: string, apres: string): LigneDiff[] {
  const a = avant.split("\n");
  const b = apres.split("\n");

  let debut = 0;
  while (debut < a.length && debut < b.length && a[debut] === b[debut]) debut++;
  let finA = a.length;
  let finB = b.length;
  while (finA > debut && finB > debut && a[finA - 1] === b[finB - 1]) {
    finA--;
    finB--;
  }

  const contexte = (lignes: string[]): LigneDiff[] =>
    lignes.map((texte) => ({ type: "contexte", texte }));

  return [
    ...contexte(a.slice(0, debut)),
    ...diffMilieu(a.slice(debut, finA), b.slice(debut, finB)),
    ...contexte(a.slice(finA)),
  ];
}

function diffMilieu(a: string[], b: string[]): LigneDiff[] {
  const n = a.length;
  const m = b.length;
  if (n * m > CELLULES_MAX) {
    return [
      ...a.map((texte): LigneDiff => ({ type: "retrait", texte })),
      ...b.map((texte): LigneDiff => ({ type: "ajout", texte })),
    ];
  }

  // Build LCS table
  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  );
  for (let i = 1; i <= n; i++) {
    for (let j = 1; j <= m; j++) {
      dp[i]![j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1]![j - 1]! + 1
          : Math.max(dp[i - 1]![j]!, dp[i]![j - 1]!);
    }
  }

  // Backtrack, then reverse: `unshift` in the loop was quadratic.
  const result: LigneDiff[] = [];
  let i = n;
  let j = m;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      result.push({ type: "contexte", texte: a[i - 1]! });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i]![j - 1]! >= dp[i - 1]![j]!)) {
      result.push({ type: "ajout", texte: b[j - 1]! });
      j--;
    } else {
      result.push({ type: "retrait", texte: a[i - 1]! });
      i--;
    }
  }
  return result.reverse();
}
