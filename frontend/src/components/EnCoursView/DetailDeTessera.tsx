import Button from "../../design/ui/Button";
import type { SalleTessera } from "../../types/salleTessera";
import { lignesDeLaCi, lignesDesRuns, lignesDuJournal, type EcranDeTessera } from "./lignesDeTessera";

const TITRE: Record<EcranDeTessera, string> = {
  runs: "Runs en cours et leur file",
  ci: "PR que le CIWatcher attend",
  journal: "Fin de tessera.log",
};

const VIDE: Record<EcranDeTessera, string> = {
  runs: "Aucun run en cours.",
  ci: "Aucune PR en attente de CI ou de merge.",
  journal: "Journal vide.",
};

interface DetailDeTesseraProps {
  ecran: EcranDeTessera;
  salle: SalleTessera;
  onFermer: () => void;
}

/**
 * Le détail d'un écran de la salle Tessera, déplié sous la salle — ticket-726 :
 * toute la file (et pas seulement les trois suivants du mur), toutes les PR en
 * attente, ou les cent dernières lignes du journal. Échap le referme, quand le
 * focus est dedans, comme le journal d'un service.
 */
export default function DetailDeTessera({ ecran, salle, onFermer }: DetailDeTesseraProps) {
  const lignes =
    ecran === "runs"
      ? lignesDesRuns(salle, Number.POSITIVE_INFINITY)
      : ecran === "ci"
        ? lignesDeLaCi(salle)
        : lignesDuJournal(salle.journal);
  return (
    <section
      id="detail-tessera"
      aria-label={TITRE[ecran]}
      data-detail-tessera={ecran}
      className="flex flex-col border-t border-violet-700 bg-zinc-950"
      onKeyDown={(e) => {
        if (e.key === "Escape") onFermer();
      }}
    >
      <header className="flex items-center gap-3 border-b border-zinc-800 px-4 py-2">
        <h4 className="text-sm font-semibold text-zinc-100">{TITRE[ecran]}</h4>
        <span className="text-xs text-zinc-500">{lignes.length} ligne{lignes.length > 1 ? "s" : ""}</span>
        <span className="ml-auto">
          <Button taille="compact" onClick={onFermer} aria-label="Fermer le détail">
            Fermer
          </Button>
        </span>
      </header>
      <ol className="max-h-80 overflow-auto py-2 font-mono text-xs leading-relaxed">
        {lignes.length === 0 && <li className="px-4 text-zinc-500">{VIDE[ecran]}</li>}
        {lignes.map((ligne) => (
          <li key={ligne.cle} className={`whitespace-pre-wrap break-words px-4 ${ligne.ton}`}>
            {ligne.texte}
          </li>
        ))}
      </ol>
    </section>
  );
}
