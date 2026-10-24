import Dossier from "../../design/bureau/Dossier";
import type { StreamState } from "../../hooks/streamState";
import { useRestants } from "../../hooks/useRestants";

interface DossiersProps {
  projet: string;
  runId: string | null;
  etat: StreamState;
}

/** La pile : un dossier par ticket restant dans la file, rien quand il n'en reste aucun (ADR-058). */
export default function Dossiers({ projet, runId, etat }: DossiersProps) {
  const restants = useRestants(projet, runId, etat);
  if (restants.length === 0) return null;

  return (
    <ul aria-label={`Tickets restants : ${restants.length}`} className="flex flex-wrap items-end gap-0.5">
      {restants.map((ticket) => (
        <li key={ticket} title={ticket}>
          <Dossier />
        </li>
      ))}
    </ul>
  );
}
