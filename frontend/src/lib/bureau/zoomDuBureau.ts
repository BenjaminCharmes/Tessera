/**
 * Le zoom de la vue Bureau — ticket-657.
 *
 * Dézoomer le navigateur faisait tenir toutes les pièces à l'écran, mais rendait le
 * reste de l'app illisible. Le Bureau a donc son propre zoom : un pas fixe, ou
 * « ajusté » pour que toutes les pièces tiennent dans la hauteur disponible.
 */
export type ModeDeZoom = number | "ajuste";

export const ZOOM_MIN = 0.4;
export const ZOOM_MAX = 1.25;
export const PAS_DE_ZOOM = 0.1;

function borne(zoom: number): number {
  return Math.round(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom)) * 100) / 100;
}

/** Le zoom suivant d'un pas, borné ; depuis « ajusté », on part du zoom affiché. */
export function zoomVoisin(actuel: number, sens: 1 | -1): number {
  return borne(actuel + sens * PAS_DE_ZOOM);
}

/**
 * Le zoom qui fait tenir un contenu de hauteur naturelle `hauteurNaturelle` dans
 * `hauteurDispo`. Jamais au-delà de 1 : « ajuster » ne grossit pas un Bureau qui tient
 * déjà. Une mesure nulle (vue masquée, jsdom) laisse le zoom à 1.
 */
export function zoomPourAjuster(
  hauteurDispo: number,
  hauteurNaturelle: number,
): number {
  if (hauteurDispo <= 0 || hauteurNaturelle <= 0) return 1;
  return Math.max(
    ZOOM_MIN,
    Math.min(1, Math.floor((hauteurDispo / hauteurNaturelle) * 100) / 100),
  );
}

export function estModeDeZoom(v: unknown): v is ModeDeZoom {
  return (
    v === "ajuste" || (typeof v === "number" && v >= ZOOM_MIN && v <= ZOOM_MAX)
  );
}
