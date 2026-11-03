import { screen } from "@testing-library/react";

/** Les boutons de la vue rendue qui portent la variante `plein` (fond violet). */
export function boutonsPleins(): HTMLElement[] {
  return screen
    .queryAllByRole("button")
    .filter((bouton) => /(^|\s)bg-violet-500(\s|$)/.test(bouton.className));
}

/** Les pastilles `StatusPill` rendues dans le document. */
export function pastilles(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>("[data-etat]"));
}
