import type { ServiceActif } from "../../types/api";
import { etatDuService, libelleDeLEtat } from "../../design/etatDuService";
import { PASTILLE_DE_L_ETAT, TEXTE_DE_L_ETAT } from "../../design/bureau/tons";
import { niveauDeLigne, TON_DE_LIGNE } from "./journal";
import MoniteurMural from "./MoniteurMural";

interface EcranMuralProps {
  service: ServiceActif;
  /** Le journal de ce service est ouvert sous la salle. */
  deplie: boolean;
  /** Ouvre le journal, ou le referme s'il est déjà ouvert. */
  onBasculer: () => void;
}

const LIGNES_VISIBLES = 4;

/**
 * Le moniteur accroché au mur pour un service lancé par l'IDE — ticket-711. Il
 * montre les dernières lignes que le backend a gardées (`sortie`) ; un clic ouvre
 * le journal complet sous la salle, un second le referme. Le voyant du cadre dit
 * l'état du service (ADR-058).
 */
export default function EcranMural({ service, deplie, onBasculer }: EcranMuralProps) {
  const sortie = service.sortie ?? [];
  const debut = Math.max(0, sortie.length - LIGNES_VISIBLES);
  const etat = etatDuService(service);
  return (
    <MoniteurMural
      titre={service.nom}
      statut={<span className={TEXTE_DE_L_ETAT[etat]}>{libelleDeLEtat(service)}</span>}
      lignes={sortie.slice(debut).map((texte, i) => ({
        cle: debut + i,
        texte,
        ton: TON_DE_LIGNE[niveauDeLigne(texte)],
      }))}
      voyant={PASTILLE_DE_L_ETAT[etat]}
      vide="(rien d'écrit pour l'instant)"
      onClick={onBasculer}
      deplie={deplie}
      controle={`journal-${service.project_id}-${service.nom}`}
      data={{ "data-ecran-mural": service.nom }}
    />
  );
}
