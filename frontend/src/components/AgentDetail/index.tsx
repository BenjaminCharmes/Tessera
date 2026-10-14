import { useState } from "react";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import ViewSwitcher, { type OptionVue } from "../../design/ui/ViewSwitcher";
import Comparer from "./Comparer";
import Fiche from "./Fiche";

/**
 * L'onglet Agents au centre : la fiche d'un rôle, ou tous les rôles comparés
 * (ticket-429). La fiche reprend la définition d'un agent de ticket-076 — son
 * prompt système, première chose à lire quand il se comporte mal.
 *
 * Le rail dit *quel* agent, le centre montre *ce qu'il est*.
 */
interface AgentDetailProps {
  role: string | null;
  /** Le projet actif : le modèle se règle projet par projet (ticket-080). */
  projectId?: string | null;
  /** Choisit un rôle, comme le rail : le tableau « Comparer » l'utilise. */
  onSelectRole?: (role: string) => void;
}

type Vue = "fiche" | "comparer";

const VUES: OptionVue<Vue>[] = [
  { valeur: "fiche", libelle: "Fiche" },
  { valeur: "comparer", libelle: "Comparer" },
];

export default function AgentDetail({
  role,
  projectId = null,
  onSelectRole,
}: AgentDetailProps) {
  const [vue, setVue] = useState<Vue>("fiche");

  function ouvrirLaFiche(cible: string) {
    onSelectRole?.(cible);
    setVue("fiche");
  }

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Agents</RegionTitle>
        <ViewSwitcher options={VUES} valeur={vue} onChange={setVue} />
      </div>
      {vue === "fiche" ? (
        <Fiche role={role} projectId={projectId} />
      ) : (
        <Comparer projectId={projectId} onOpen={ouvrirLaFiche} />
      )}
    </div>
  );
}
