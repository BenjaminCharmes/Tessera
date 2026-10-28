import type { ServiceActif } from "../../types/api";

// Les serveurs de dev colorent leur sortie : l'adresse se lit une fois les codes ANSI retirés.
const ANSI = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, "g");
const ADRESSE = /https?:\/\/(?:localhost|127\.0\.0\.1):\d+\/?/;

/**
 * L'adresse locale qu'un service lancé a annoncée dans sa sortie, ou null — ticket-622.
 *
 * Un service arrêté n'en a pas, même si sa dernière sortie en citait une : la
 * baie n'ouvre que ce qui répond.
 */
export function adresseDeLApp(
  services: readonly ServiceActif[],
): string | null {
  for (const service of services) {
    if (!service.en_cours) continue;
    for (const ligne of service.sortie ?? []) {
      const trouve = ligne.replace(ANSI, "").match(ADRESSE);
      if (trouve) return trouve[0];
    }
  }
  return null;
}
