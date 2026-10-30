import { etatDuService, libelleDeLEtat, type EtatDuService } from "../../design/etatDuService";
import type { AppEnCours, ServiceActif } from "../../types/api";

/** Une baie de la salle : un service, son état et la phrase qui le dit au lecteur d'écran. */
export interface BaieDeSalle {
  nom: string;
  etat: EtatDuService;
  libelle: string;
}

/**
 * Les baies d'une salle de projet — ticket-710 : une par service déclaré, lu de
 * l'API. Une app de l'inventaire qu'aucun service déclaré ne nomme (lancée à la
 * main, ou lecture en échec) a aussi sa baie : elle figure dans l'inventaire,
 * donc elle tourne.
 */
export function baiesDuProjet(
  apps: readonly AppEnCours[],
  services: readonly ServiceActif[],
): BaieDeSalle[] {
  const baies: BaieDeSalle[] = services.map((service) => ({
    nom: service.nom,
    etat: etatDuService(service),
    libelle: libelleDeLEtat(service),
  }));
  for (const app of apps) {
    if (!baies.some((baie) => baie.nom === app.nom)) {
      baies.push({ nom: app.nom, etat: "en-cours", libelle: "en cours" });
    }
  }
  return baies;
}
