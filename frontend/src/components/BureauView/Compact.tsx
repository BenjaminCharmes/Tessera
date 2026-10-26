import Pastille from "../../design/bureau/Pastille";
import { TON_PUCE } from "../../design/bureau/tons";
import type { StreamState } from "../../hooks/streamState";
import { libelleDuPoste } from "../../lib/bureau/libelleDuPoste";
import { postesDuRun } from "../../lib/bureau/postesDuRun";
import { santeAgent } from "../../lib/santeAgent";

interface CompactProps {
  projet: string;
  etat: StreamState;
  maintenant: number;
}

/** La rangée compacte d'un projet : cinq puces de poste et, si un agent travaille, sa santé. */
export default function Compact({ projet, etat, maintenant }: CompactProps) {
  const postes = postesDuRun(etat);
  const sante = santeAgent(
    etat.dernierEvenementA,
    maintenant,
    etat.pendingQuestion,
    etat.attenteExterieure !== null,
  );
  const enCours = postes.some((p) => p.etat === "occupe");

  return (
    <div
      role="group"
      aria-label={projet}
      className="flex items-center gap-3 rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2"
    >
      <span className="w-40 truncate text-corps font-semibold text-zinc-200">{projet}</span>
      <div className="flex items-center gap-1.5">
        {postes.map((p) => (
          <span
            key={p.poste}
            role="img"
            aria-label={libelleDuPoste(p.poste, p.etat, sante)}
            className={`size-2.5 rounded-sm ${TON_PUCE[p.etat === "occupe" ? sante : p.etat]}`}
          />
        ))}
      </div>
      {enCours && <Pastille sante={sante} />}
    </div>
  );
}
