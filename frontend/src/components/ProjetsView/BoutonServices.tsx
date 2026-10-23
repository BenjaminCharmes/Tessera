import { useState } from "react";
import Button from "../../design/ui/Button";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";

interface BoutonServicesProps {
  projet: ProjectOverview;
  /** Appelé après un lancement ou un arrêt réussi : la vue relit l'état réel. */
  onChange: () => void;
}

/**
 * Lance ou arrête l'app d'un projet depuis sa carte — ticket-411.
 *
 * Sans service déclaré, rien n'est rendu : le mode d'emploi vit dans la vue
 * du projet. Le clic ne remonte pas à la carte, qui ouvrirait les tickets.
 */
export default function BoutonServices({ projet, onChange }: BoutonServicesProps) {
  const [occupe, setOccupe] = useState(false);
  const [echec, setEchec] = useState<string | null>(null);

  if (!projet.services_declares) return null;

  async function basculer() {
    setOccupe(true);
    setEchec(null);
    try {
      if (projet.services_en_cours) await api.services.stop(projet.id);
      else await api.services.start(projet.id);
      onChange();
    } catch (e) {
      setEchec(e instanceof Error ? e.message : "Action impossible");
    } finally {
      setOccupe(false);
    }
  }

  return (
    <div className="flex min-w-0 shrink-0 flex-col items-end gap-1">
      <Button
        taille="compact"
        variante={projet.services_en_cours ? "arret" : "borde"}
        disabled={occupe}
        onClick={(e) => {
          e.stopPropagation();
          void basculer();
        }}
      >
        {projet.services_en_cours ? "Arrêter" : "Lancer"}
      </Button>
      {echec && (
        <p role="alert" className="line-clamp-2 max-w-48 text-right text-micro text-red-400">
          {echec}
        </p>
      )}
    </div>
  );
}
