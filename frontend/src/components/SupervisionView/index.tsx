import { useState } from "react";
import ViewSwitcher from "../../design/ui/ViewSwitcher";
import type { OptionVue } from "../../design/ui/ViewSwitcher";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { Project, ServiceActif } from "../../types/api";
import type { ReglageSon } from "../BureauView/ColonneAToi";
import BureauConnecte from "./BureauConnecte";
import ListeView from "./ListeView";

type Vue = "bureau" | "liste";

const VUES: OptionVue<Vue>[] = [
  { valeur: "bureau", libelle: "Bureau" },
  { valeur: "liste", libelle: "Liste" },
];

/** Tant que personne n'a branché le réglage, le Bureau reste muet. */
const SON_COUPE: ReglageSon = { actif: false, regler: () => undefined };

interface SupervisionViewProps {
  supervision: UseSupervisionResult;
  projects: Project[];
  /** Les services lancés, listés à part des runs (ticket-138). */
  services?: ServiceActif[];
  /** Le réglage « Son » de la question, tenu par la cloche (ticket-554). */
  son?: ReglageSon;
}

/**
 * Supervision : le Bureau par défaut, la Liste à un clic (ticket-567).
 *
 * Les deux vues lisent le même store de run : le choix ne change que la
 * manière de regarder, jamais ce qu'on voit (ADR-034).
 */
export default function SupervisionView({
  supervision,
  projects,
  services = [],
  son = SON_COUPE,
}: SupervisionViewProps) {
  const [vue, setVue] = useState<Vue>("bureau");
  const selecteur = (
    <ViewSwitcher label="Vue de la supervision" options={VUES} valeur={vue} onChange={setVue} />
  );

  return vue === "bureau" ? (
    <BureauConnecte
      supervision={supervision}
      projects={projects}
      services={services}
      son={son}
      selecteur={selecteur}
    />
  ) : (
    <ListeView
      supervision={supervision}
      projects={projects}
      services={services}
      selecteur={selecteur}
    />
  );
}
