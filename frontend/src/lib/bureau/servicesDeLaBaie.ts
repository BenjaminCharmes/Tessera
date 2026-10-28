import type { UseServicesResult } from "../../hooks/useServices";

/**
 * Les services que la baie montre — ticket-632.
 *
 * Le projet qui fait tourner l'IDE a été lancé hors du registre de services
 * (`tessera.ps1`) : le registre le croit éteint alors qu'il sert cette page.
 * Ses serveurs se montrent donc allumés tant que l'IDE tourne.
 */
export function servicesDeLaBaie(
  services: UseServicesResult,
  faitTournerLIde: boolean,
): UseServicesResult {
  if (!faitTournerLIde) return services;
  return {
    ...services,
    enCours: true,
    enEchec: false,
    services: services.services.map((s) => ({
      ...s,
      en_cours: true,
      code_de_sortie: null,
    })),
  };
}
