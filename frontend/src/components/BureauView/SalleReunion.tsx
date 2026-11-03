import type { OccupantDeReunion } from "../../lib/bureau/salles";
import Agrandi from "../../design/bureau/Agrandi";
import AgentDebout from "../../design/bureau/AgentDebout";
import Chaise from "../../design/bureau/Chaise";
import TableDeReunion from "../../design/bureau/TableDeReunion";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { visiteur } from "../../lib/bureau/noms";
import Salle from "./Salle";

interface SalleReunionProps {
  occupants: readonly OccupantDeReunion[];
  /** L'horloge unique de la vue (ticket-602). */
  maintenant: number;
}

/** « 2 fichiers », « 1 fichier », ou « fichiers inconnus » quand l'événement n'en nomme aucun. */
function decompte(fichiers: readonly string[]): string {
  if (fichiers.length === 0) return "fichiers inconnus";
  return `${fichiers.length} fichier${fichiers.length > 1 ? "s" : ""}`;
}

/**
 * Un conflit confié au résolveur : ses fichiers pendant le travail, puis la PR
 * à relire, que rien ne mergera seule (ADR-033).
 */
export default function SalleReunion({
  occupants,
  maintenant,
}: SalleReunionProps) {
  return (
    <Salle
      maintenant={maintenant}
      titre="Salle de réunion"
      entete="un conflit de rebase confié au résolveur : ses fichiers pendant le travail, puis la PR à relire"
      vide="Aucun conflit en cours"
      mobilier={
        <div className="flex items-end gap-1">
          <Chaise />
          <TableDeReunion />
          <Chaise />
        </div>
      }
      textes={occupants.map(({ projet, reunion }) => (
        <li
          key={projet}
          className="truncate"
          title={
            reunion.temps === "conflit"
              ? reunion.fichiers.join(", ")
              : undefined
          }
        >
          <span className="text-zinc-400">{projet}</span> · résolveur{" "}
          {reunion.temps === "conflit" ? (
            <span className="text-amber-300">
              Résolution en cours · {decompte(reunion.fichiers)}
              {reunion.fichiers.length > 0 &&
                ` : ${reunion.fichiers.join(", ")}`}
            </span>
          ) : (
            <span className="text-blue-300">PR #{reunion.pr} à relire</span>
          )}
        </li>
      ))}
    >
      {/* Le résolveur ne se dessine que pendant la résolution : la PR à relire n'est plus son travail (ADR-033). */}
      {occupants.flatMap(({ projet, reunion }) =>
        reunion.temps === "conflit"
          ? [
              <li key={projet} data-agent="resolveur" title={visiteur(projet, "resolveur", nomDuPoste("resolveur"))}>
                <Agrandi>
                  <AgentDebout projet={projet} role="resolveur" />
                </Agrandi>
              </li>,
            ]
          : [],
      )}
    </Salle>
  );
}
