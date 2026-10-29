import { etatDuService, libelleDeLEtat, type EtatDuService } from "../../design/etatDuService";
import type { AppEnCours, ServiceActif } from "../../types/api";

/** Une baie de la salle : un service, son état et la phrase qui le dit au lecteur d'écran. */
export interface BaieDeSalle {
  nom: string;
  etat: EtatDuService;
  libelle: string;
}

/**
 * Les baies d'une salle : un étage par service déclaré du projet, lu de l'API.
 * Sans service connu (app lancée à la main, lecture en échec), l'app elle-même
 * est la seule baie : elle figure dans l'inventaire, donc elle tourne.
 */
export function baiesDeLApp(app: AppEnCours, services: readonly ServiceActif[]): BaieDeSalle[] {
  if (services.length === 0) {
    return [{ nom: app.nom, etat: "en-cours", libelle: "en cours" }];
  }
  return services.map((service) => ({
    nom: service.nom,
    etat: etatDuService(service),
    libelle: libelleDeLEtat(service),
  }));
}
