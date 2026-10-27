import type { Project } from "../../types/api";
import CreateProjectModal from "../Sidebar/CreateProjectModal";
import ImportProjectModal from "../Sidebar/ImportProjectModal";

export type ModaleDeProjet = "import" | "creation" | null;

interface ModalesDeProjetProps {
  ouverte: ModaleDeProjet;
  onFermer: () => void;
  /** Un projet vient d'être créé ou importé. */
  onAjoute: (project: Project) => void;
}

/** La modale de création ou d'import ouverte depuis la barre de la vue Projets. */
export default function ModalesDeProjet({
  ouverte,
  onFermer,
  onAjoute,
}: ModalesDeProjetProps) {
  if (ouverte === "creation") {
    return <CreateProjectModal onClose={onFermer} onCreated={onAjoute} />;
  }
  if (ouverte === "import") {
    return <ImportProjectModal onClose={onFermer} onProjectCreated={onAjoute} />;
  }
  return null;
}
