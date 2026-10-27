import type { OccupantDeReunion } from "../../lib/bureau/salles";
import TableDeReunion from "../../design/bureau/TableDeReunion";
import Salle from "./Salle";

interface SalleReunionProps {
  occupants: readonly OccupantDeReunion[];
}

/**
 * Un conflit confié au résolveur : ses fichiers pendant le travail, puis la PR
 * à relire, que rien ne mergera seule (ADR-033).
 */
export default function SalleReunion({ occupants }: SalleReunionProps) {
  return (
    <Salle
      titre="Salle de réunion"
      entete="conflit de rebase"
      vide="Aucun conflit en cours"
      mobilier={<TableDeReunion />}
    >
      {occupants.map(({ projet, reunion }) => (
        <li key={projet} className="text-xs">
          <span className="text-zinc-400">{projet}</span>{" "}
          {reunion.temps === "conflit" ? (
            <span className="text-amber-300">
              Résolution en cours : {reunion.fichiers.length > 0 ? reunion.fichiers.join(", ") : "fichiers inconnus"}
            </span>
          ) : (
            <span className="text-blue-300">PR #{reunion.pr} à relire</span>
          )}
        </li>
      ))}
    </Salle>
  );
}
