import { useState } from "react";
import Button from "../../design/ui/Button";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";

/** Une bulle au-dessus du bouton : un message ne pousse pas la carte (ticket-633). */
export const BULLE =
  "absolute right-0 bottom-full z-10 mb-1 w-56 rounded-sm border border-zinc-700 bg-zinc-900 p-1.5 text-right text-micro shadow-lg";

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
export default function BoutonServices({
  projet,
  onChange,
}: BoutonServicesProps) {
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
    <div className="relative shrink-0">
      <Button
        taille="compact"
        variante={projet.services_en_cours ? "arret" : "borde"}
        disabled={occupe}
        onClick={(e) => {
          e.stopPropagation();
          void basculer();
        }}
      >
        {/* « l'app » : à côté de « File », deux « Lancer » se confondaient (ticket-633). */}
        {projet.services_en_cours ? "Arrêter l'app" : "Lancer l'app"}
      </Button>
      {echec && (
        <p role="alert" className={`${BULLE} text-red-400`}>
          {echec}
        </p>
      )}
    </div>
  );
}
