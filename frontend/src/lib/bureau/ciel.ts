/** Ce qu'une fenêtre montre de jour : le soleil, et zéro à deux nuages. */
export interface CielDeFenetre {
  soleil: boolean;
  nuages: 0 | 1 | 2;
}

function graine(texte: string): number {
  let h = 7;
  for (let i = 0; i < texte.length; i += 1) h = (h * 31 + texte.charCodeAt(i)) % 100003;
  return h;
}

function jourLocal(maintenant: number): string {
  const d = new Date(maintenant);
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

/**
 * Le ciel des `nombre` fenêtres d'une salle. Un seul soleil dans tout le Bureau :
 * la salle qui le porte le montre dans sa première fenêtre, les autres n'en ont pas.
 * Les nuages varient d'une salle et d'un jour à l'autre, mais pas d'un rendu à
 * l'autre : le tirage est une graine de la salle et de la date (ADR-058, le hasard
 * ne change que la façon de montrer un état réel, ici le jour).
 */
export function cielDesFenetres(
  cle: string,
  nombre: number,
  maintenant: number,
  avecSoleil = false,
): CielDeFenetre[] {
  const jour = jourLocal(maintenant);
  return Array.from({ length: nombre }, (_, i): CielDeFenetre => {
    const soleil = avecSoleil && i === 0;
    const tirage = graine(`${cle}|${jour}|${i}`) % 3;
    const nuages: 0 | 1 | 2 = tirage === 0 ? 0 : tirage === 1 || soleil ? 1 : 2;
    return { soleil, nuages };
  });
}
