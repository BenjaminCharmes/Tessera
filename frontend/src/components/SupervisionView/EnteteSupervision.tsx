import type { ReactNode } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import StatusPill from "../../design/ui/StatusPill";
import type { EntreeMenuFermer } from "./MenuFermer";
import MenuFermer from "./MenuFermer";
import type { IssueDuRun } from "./issueDuRun";

interface EnteteSupervisionProps {
  nombreDeRuns: number;
  connecte: boolean;
  /** Les entrées du menu de rangement ; le menu n'apparaît que si un run est clos. */
  entrees: EntreeMenuFermer[];
  onFermer: (issue: IssueDuRun | null) => void;
  /** Le sélecteur Bureau / Liste, posé par la vue d'ensemble. */
  selecteur?: ReactNode;
}

function etiquette(nombre: number): string {
  if (nombre === 0) return "rien en cours";
  return `${nombre} run${nombre > 1 ? "s" : ""}`;
}

/** La bande d'en-tête commune à la Liste et au Bureau : titre, rangement par lot, état du canal. */
export default function EnteteSupervision({
  nombreDeRuns,
  connecte,
  entrees,
  onFermer,
  selecteur,
}: EnteteSupervisionProps) {
  const totalClos = entrees.find((e) => e.issue === null)?.count ?? 0;
  return (
    <div className={`${BAND} justify-between border-b border-zinc-800 px-3`}>
      <RegionTitle>Supervision</RegionTitle>
      <div className="flex items-center gap-3">
        {selecteur}
        {totalClos > 0 && <MenuFermer entrees={entrees} onFermer={onFermer} />}
        <StatusPill
          etat={!connecte ? "attention" : nombreDeRuns > 0 ? "en-cours" : "neutre"}
          libelle={connecte ? etiquette(nombreDeRuns) : "hors ligne"}
        />
      </div>
    </div>
  );
}
