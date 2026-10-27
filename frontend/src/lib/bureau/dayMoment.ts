/** Le ciel que montrent les fenêtres : jour ou nuit. */
export type DayMoment = "jour" | "nuit";

/** Le jour va de 7 h (inclus) à 19 h (exclu), heure locale. */
const FIRST_DAY_HOUR = 7;
const FIRST_NIGHT_HOUR = 19;

/**
 * Le moment du jour à l'instant `now` (millisecondes). L'instant vient de
 * l'horloge unique de la vue : aucun minuteur n'est ouvert ici.
 */
export function dayMoment(now: number): DayMoment {
  const hour = new Date(now).getHours();
  return hour >= FIRST_DAY_HOUR && hour < FIRST_NIGHT_HOUR ? "jour" : "nuit";
}
