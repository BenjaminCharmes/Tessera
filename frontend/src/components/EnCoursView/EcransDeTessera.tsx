import type { SalleTessera } from "../../types/salleTessera";
import MoniteurMural from "./MoniteurMural";
import { TON_DU_NIVEAU, lignesDeLaCi, lignesDesRuns, lignesDuJournal, type EcranDeTessera } from "./lignesDeTessera";

/**
 * Les trois moniteurs du mur de la salle Tessera — ticket-726 : les runs vivants et
 * leur file, les PR que le CIWatcher attend, la fin de `tessera.log`. Chaque ligne
 * vient de `GET /tessera/salle` ; sans donnée, l'écran le dit (ADR-058). Un clic
 * déplie son détail sous la salle, un second le referme.
 */
interface EcransDeTesseraProps {
  salle: SalleTessera;
  deplie: EcranDeTessera | null;
  /** Ouvre le détail d'un écran sous la salle, ou le referme s'il est déjà ouvert. */
  onBasculer: (ecran: EcranDeTessera) => void;
}

export default function EcransDeTessera({ salle, deplie, onBasculer }: EcransDeTesseraProps) {
  const file = salle.runs.find((r) => r.file_total > 0);
  const enAttente = Object.values(salle.ci_en_attente).reduce((n, t) => n + t.length, 0);
  const erreurs = salle.journal.some((l) => TON_DU_NIVEAU[l.niveau] === "text-red-300");
  return (
    <div className="mx-auto grid max-w-6xl grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-x-6 gap-y-4">
      <MoniteurMural
        titre="runs en cours"
        statut={file ? <span className="text-blue-300">file {file.file_index} / {file.file_total}</span> : `${salle.runs.length}`}
        lignes={lignesDesRuns(salle)}
        voyant={salle.runs.length > 0 ? "bg-blue-400" : "bg-zinc-600"}
        vide="(aucun run)"
        data={{ "data-ecran-tessera": "runs" }}
        onClick={() => onBasculer("runs")}
        deplie={deplie === "runs"}
        controle="detail-tessera"
      />
      <MoniteurMural
        titre="CIWatcher"
        statut={`${enAttente} PR`}
        lignes={lignesDeLaCi(salle)}
        voyant={enAttente > 0 ? "bg-amber-400" : "bg-zinc-600"}
        vide="(aucune PR en attente)"
        data={{ "data-ecran-tessera": "ci" }}
        onClick={() => onBasculer("ci")}
        deplie={deplie === "ci"}
        controle="detail-tessera"
      />
      <MoniteurMural
        titre="tessera.log"
        statut={erreurs ? <span className="text-red-300">erreur</span> : "ok"}
        lignes={lignesDuJournal(salle.journal)}
        voyant={erreurs ? "bg-red-500" : "bg-blue-400"}
        vide="(journal vide)"
        data={{ "data-ecran-tessera": "journal" }}
        onClick={() => onBasculer("journal")}
        deplie={deplie === "journal"}
        controle="detail-tessera"
      />
    </div>
  );
}
