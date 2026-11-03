import type { Physique } from "../physique";
import { E, type Grille, R, type Sprite, cuire, sprite } from "./grille";
import { tete } from "./poste";

/*
 * La salle d'un produit (ticket-727) : l'agent de produit assis à son pupitre de
 * console, le pupitre vide, la baie GPU d'Ollama. Même grammaire que l'atelier :
 * rampes de quatre tons, contour sélectif, jetons. L'agent réutilise la tête du
 * Bureau ; sa tenue unie est la famille `haut-produit`. Seuls l'écran et le voyant
 * portent un état (ADR-058), en jetons `etat-*` (ADR-026).
 */

/** Ce que montre l'écran de la console : il travaille, il attend devant, personne. */
export type EcranDeConsole = "allume" | "attente" | "eteint";

/** Les lignes de l'écran allumé, en motif répété. */
const LIGNES = [6, 4, 6, 3, 5, 6] as const;

/** La chaise vue de dos, sous l'agent : celle du poste du Bureau. */
function chaise(g: Grille, vide: boolean): void {
  const C = R("chaise");
  g.rect(6, 13, 18, 11, C.s);
  g.rect(7, 12, 16, 1, C.b);
  g.rect(7, 13, 16, 1, C.hi);
  g.rect(14, 28, 2, 5, C.s);
  g.rect(14, 28, 1, 5, C.b);
  g.rect(9, 33, 12, 1, C.d);
  g.rect(10, 33, 10, 1, C.s);
  for (const x of [9, 14, 20]) g.px(x, 34, C.d);
  if (vide) {
    g.rect(6, 20, 18, 4, C.b);
    g.rect(6, 20, 18, 1, C.hi);
  }
}

/** Le pupitre : façade de métal, rangée de touches en relief, fentes, deux pieds. */
function pupitre(g: Grille): void {
  const M = R("metal");
  const K = R("clavier");
  g.rect(2, 24, 36, 1, M.hi);
  g.rect(2, 25, 36, 3, M.b);
  g.rect(2, 25, 1, 3, M.hi);
  for (let x = 8; x <= 28; x += 4) {
    g.rect(x, 25, 2, 2, K.b);
    g.px(x, 25, K.hi);
    g.px(x + 1, 26, K.s);
  }
  g.rect(2, 28, 36, 2, M.s);
  g.rect(2, 29, 36, 1, M.d);
  for (let x = 12; x < 28; x += 2) g.px(x, 28, M.d);
  for (const x of [4, 34]) {
    g.rect(x, 30, 2, 6, M.b);
    g.rect(x + 1, 30, 1, 6, M.s);
    g.px(x, 30, M.d);
  }
}

/** Le moniteur sur pied, à droite : la coque ; l'écran se dessine dans son propre calque. */
function moniteur(g: Grille): void {
  const M = R("metal");
  const F = R("cadre");
  g.rect(30, 18, 4, 5, M.s);
  g.rect(30, 18, 1, 5, M.b);
  g.rect(28, 22, 8, 2, M.b);
  g.rect(28, 22, 8, 1, M.hi);
  g.rect(26, 6, 12, 12, F.b);
  g.rect(26, 6, 12, 1, F.hi);
  g.rect(26, 7, 1, 10, F.hi);
  g.rect(37, 7, 1, 11, F.s);
  g.rect(27, 17, 10, 1, F.s);
}

/** L'écran, 8 × 8 en (28, 8) : allumé, quatre images font défiler le texte ; en attente, trois points. */
function ecran(s: ReturnType<typeof sprite>, quoi: EcranDeConsole): void {
  const L = E("actif");
  const A = E("attente");
  const fond = s.calque();
  if (quoi === "allume") {
    fond.rect(28, 8, 8, 8, L.d);
    for (let k = 0; k < 4; k++) {
      const style: Record<string, string> = { animationDuration: "1.2s", animationDelay: `-${(k * 0.3).toFixed(1)}s` };
      if (k) style.opacity = "0";
      const f = s.calque("anim-trame anim-trame-4", style);
      for (let i = 0; i < 8; i++) {
        const y = 9 + 2 * i - 2 * k;
        if (y < 9 || y > 14) continue;
        const w = LIGNES[i % LIGNES.length] ?? 4;
        f.rect(29, y, w, 1, L.b);
        f.px(29, y, L.hi);
        if (w > 4) f.px(29 + w - 1, y, L.hi);
      }
    }
    return;
  }
  fond.rect(28, 8, 8, 8, "cadre.d");
  if (quoi === "attente") for (const x of [28, 31, 34]) fond.rect(x, 11, 2, 2, A.hi);
  else {
    fond.line(29, 11, 31, 9, "cadre.s");
    fond.px(29, 12, "cadre.s");
  }
}

/** L'agent de produit à son pupitre, grille 40 × 36 : au travail il tape, au repos ses bras pendent. */
export function agentAuPupitre(ph: Physique, etat: "actif" | "repos"): Sprite {
  const s = sprite(40, 36);
  const T = R("haut-produit");
  const K = R(`peau${ph.peau}`);
  chaise(s.calque(), false);
  const g = s.calque();
  tete(g, 9, 6, ph, etat === "actif" ? "actif" : "attente");
  g.rect(13, 15, 4, 1, K.s);
  g.rect(8, 16, 14, 8, T.b);
  g.rect(7, 17, 16, 7, T.b);
  g.rect(19, 17, 4, 7, T.s);
  g.rect(8, 17, 4, 1, T.hi);
  g.px(8, 18, T.hi);
  for (const x of [10, 17]) {
    g.rect(x, 28, 3, 6, "pantalon.b");
    g.rect(x + 2, 28, 1, 6, "pantalon.s");
    g.rect(x - 1, 34, 4, 2, "chaussure.b");
    g.rect(x - 1, 34, 4, 1, "chaussure.hi");
  }
  pupitre(s.calque());
  const a = s.calque(etat === "actif" ? "anim-tape" : "");
  if (etat === "actif") {
    for (const x of [5, 22]) {
      a.rect(x, 18, 3, 5, T.s);
      a.rect(x, 22, 3, 2, K.b);
    }
    a.rect(5, 18, 1, 4, T.d);
  } else {
    // Au repos, les bras pendent le long du corps, les mains sous le plateau.
    for (const x of [5, 22]) a.rect(x, 17, 3, 7, T.s);
    a.rect(5, 17, 1, 7, T.d);
  }
  moniteur(s.calque());
  ecran(s, etat === "actif" ? "allume" : "attente");
  return cuire(s);
}

/** Le pupitre sans personne, grille 40 × 36 : la chaise vide, l'écran éteint. */
export function pupitreVide(): Sprite {
  const s = sprite(40, 36);
  chaise(s.calque(), true);
  pupitre(s.calque());
  moniteur(s.calque());
  ecran(s, "eteint");
  return cuire(s);
}

/** Ce que la baie d'Ollama dit : prêt à répondre, ou tenu à l'écart par le disjoncteur. */
export type EtatGpu = "disponible" | "refroidissement";

/** La baie GPU d'Ollama, 32 × 60 : trois cartes graphiques à deux ventilateurs, un voyant. */
export function baieGpu(etat: EtatGpu): Sprite {
  const s = sprite(32, 60);
  const g = s.calque();
  const M = R("metal");
  const F = R("cadre");
  g.rect(0, 0, 32, 60, M.d);
  g.rect(1, 1, 30, 58, M.b);
  g.rect(1, 1, 30, 1, M.hi);
  g.rect(1, 1, 1, 58, M.hi);
  g.rect(30, 2, 1, 57, M.s);
  g.rect(3, 3, 26, 6, M.d);
  g.rect(4, 4, 18, 4, F.d);
  g.rect(5, 5, 9, 1, M.s);
  g.rect(5, 6, 5, 1, M.s);
  for (const y of [12, 26, 40]) {
    g.rect(3, y, 26, 12, M.s);
    g.rect(4, y + 1, 24, 10, F.b);
    g.rect(4, y + 1, 24, 1, F.hi);
    g.rect(27, y + 2, 1, 9, F.s);
    for (const cx of [10, 21]) {
      g.disc(cx, y + 6, 4, "metal");
      g.rect(cx - 1, y + 5, 2, 2, M.d);
    }
    for (let x = 5; x < 27; x += 2) g.px(x, y + 11, M.d);
  }
  g.rect(2, 55, 28, 3, M.d);
  g.rect(3, 58, 4, 2, M.d);
  g.rect(25, 58, 4, 2, M.d);
  const L = E(etat === "disponible" ? "actif" : "question");
  const v = s.calque(etat === "refroidissement" ? "anim-gyro" : "");
  v.rect(23, 4, 5, 4, L.d);
  v.rect(24, 5, 3, 2, L.b);
  v.px(24, 5, L.hi);
  return cuire(s);
}
