import { useCallback, useMemo, useState } from "react";
import IconeDuProjet from "../ProjetsView/IconeDuProjet";
import { useApercuDuProjet } from "../../hooks/useApercuDesProjets";
import { useResource } from "../../hooks/useResource";
import { useQuotaLu } from "../../hooks/useQuotaLu";
import { lireLaSalleTessera } from "../../lib/apiSalleTessera";
import Agrandi from "../../design/bureau/Agrandi";
import BaieGpu from "../../design/bureau/BaieGpu";
import BoucheVMC from "../../design/bureau/BoucheVMC";
import CheminDeCables from "../../design/bureau/CheminDeCables";
import Extincteur from "../../design/bureau/Extincteur";
import PorteCoupeFeu from "../../design/bureau/PorteCoupeFeu";
import type { AppEnCours } from "../../types/api";
import type { ProcessusDeTessera, SalleTessera as Salle } from "../../types/salleTessera";
import AvecInfobulle from "../BureauView/AvecInfobulle";
import JaugesDeQuota from "../../design/ui/JaugesDeQuota";
import BaieAvecFiche from "./BaieAvecFiche";
import DetailDeTessera from "./DetailDeTessera";
import EcransDeTessera from "./EcransDeTessera";
import type { EcranDeTessera } from "./lignesDeTessera";
import SolDeSalle from "./SolDeSalle";
import { formaterHeure, formaterMo } from "./format";

interface SalleTesseraProps {
  /** Le nom affiché du projet bootstrap, lu dans la vue d'ensemble. */
  nom: string;
  /** Heure de la dernière lecture de l'inventaire : elle relance la lecture de la salle. */
  lueA: number;
}

const LIGNES_DU_JOURNAL_DEPLIE = 100;

/** Un processus de Tessera vu comme une app, pour la fiche partagée avec les autres salles. */
function commeUneApp(p: ProcessusDeTessera): AppEnCours {
  return {
    project_id: "ide-core", project_name: "Tessera", nom: p.nom, origine: "externe",
    pid: p.pid ?? 0, ports: [p.port], demarre_a: p.demarre_a, memoire_mo: p.memoire_mo,
  };
}

function Compteur({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <div className="relative w-52 rounded-sm border-[3px] border-zinc-800 bg-zinc-700 px-2.5 pb-1.5 pt-2.5 font-mono text-micro text-zinc-200 shadow-[0_3px_0_rgb(0_0_0/0.3)]">
      <span aria-hidden="true" className="absolute left-1/2 top-0.5 size-1.5 -translate-x-1/2 rounded-full bg-zinc-400" />
      <div className="mb-1 text-zinc-400">{titre}</div>
      {children}
    </div>
  );
}

/**
 * La salle des serveurs de Tessera, toujours allumée — ticket-726. Encadrée de
 * violet : c'est l'identité de Tessera, pas un état (ADR-026). Pas de bouton
 * d'arrêt : on n'éteint pas la salle d'où l'on regarde. Tout ce qui s'y allume
 * vient de `GET /tessera/salle` et du quota (ADR-058).
 */
export default function SalleTessera({ nom, lueA }: SalleTesseraProps) {
  // `lueA` change l'identité du fetcher exprès : c'est la clé de la requête.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const lire = useMemo(() => () => lireLaSalleTessera(), [lueA]);
  const { data: salle } = useResource<Salle | null>(lire, null, { projet: "ide-core", ressource: "salle-tessera" });
  const [deplie, setDeplie] = useState<EcranDeTessera | null>(null);
  const fermer = useCallback(() => setDeplie(null), []);
  // Le journal déplié lit cent lignes, et seulement tant qu'il est ouvert.
  const lireLeJournal = useMemo(
    () => (deplie === "journal" ? () => lireLaSalleTessera(LIGNES_DU_JOURNAL_DEPLIE) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [deplie, lueA],
  );
  const { data: detaillee } = useResource<Salle | null>(lireLeJournal, null);
  const fenetres = useQuotaLu(lueA);
  const apercu = useApercuDuProjet("ide-core");
  if (salle === null) return null;

  const memoire = salle.processus.reduce((s, p) => s + p.memoire_mo, 0);
  const debut = salle.processus.find((p) => p.nom === "backend")?.demarre_a ?? null;
  const refroidi = salle.ollama.refroidissement_s !== null;
  return (
    <article aria-label="Salle Tessera" data-salle-tessera className="mb-4 overflow-hidden rounded-lg border border-violet-800 bg-(--sprite-salle-mur)">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-zinc-800 bg-zinc-900/60 px-3 py-2">
        <IconeDuProjet projet={apercu ?? { id: "ide-core", name: nom, icon: false }} taille="titre" />
        <h3 className="text-sm font-semibold text-zinc-100">{nom}</h3>
        <span className="text-xs text-zinc-400">
          {salle.processus.length} services · {formaterMo(memoire)} · démarré à {formaterHeure(debut)}
        </span>
        <span className="rounded-full bg-violet-950 px-2.5 py-0.5 text-micro text-zinc-200 ring-1 ring-violet-700">fait tourner l'IDE</span>
      </header>
      <div className="relative px-6 pt-8">
        <div className="absolute inset-x-0 top-0">
          <CheminDeCables />
        </div>
        <EcransDeTessera
          salle={salle}
          deplie={deplie}
          onBasculer={(ecran) => setDeplie((avant) => (avant === ecran ? null : ecran))}
        />
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4 border-b-4 border-(--sprite-salle-plinthe)">
          <span className="flex items-end gap-4">
            {salle.processus.map((p) => (
              <BaieAvecFiche
                key={p.nom}
                baie={{ nom: p.nom, etat: p.pid === null ? "arrete" : "en-cours", libelle: p.pid === null ? "à l'arrêt" : "en cours" }}
                app={p.pid === null ? undefined : commeUneApp(p)}
              />
            ))}
            <AvecInfobulle
              label={`Ollama : ${refroidi ? "en refroidissement" : "disponible"}`}
              className="rounded-sm focus-visible:outline-2 focus-visible:outline-violet-500"
              infobulle={
                <>
                  <p className="font-semibold text-zinc-100">Ollama · {salle.ollama.url}</p>
                  <p>{refroidi ? `En refroidissement encore ${Math.ceil(salle.ollama.refroidissement_s ?? 0)} s : les rôles passent à leur repli.` : "Disponible."}</p>
                </>
              }
            >
              <Agrandi>
                <BaieGpu etat={refroidi ? "refroidissement" : "disponible"} />
              </Agrandi>
            </AvecInfobulle>
          </span>
          {/* Les compteurs sont des affiches punaisées au mur, un peu au-dessus du sol : la salle ne grandit pas. */}
          <span data-affiches className="mb-6 flex flex-wrap items-stretch justify-center gap-4">
            <Compteur titre="QUOTA DE L'ABONNEMENT">
              <JaugesDeQuota fenetres={fenetres} variante="affiche" />
            </Compteur>
            <Compteur titre="ACTIVITÉ">
              <div className={salle.agents > 0 ? "text-blue-300" : undefined}>
                {salle.agents} agent{salle.agents > 1 ? "s" : ""} au travail
              </div>
              <div>
                {salle.runs_du_jour} run{salle.runs_du_jour > 1 ? "s" : ""} aujourd&apos;hui
              </div>
              <div className="text-zinc-400">tessera.db {formaterMo(salle.base_mo)}</div>
            </Compteur>
          </span>
          <span className="flex items-end gap-4">
            <span className="self-start">
              <Agrandi>
                <BoucheVMC regime={memoire < 200 ? "lent" : memoire < 500 ? "moyen" : "rapide"} />
              </Agrandi>
            </span>
            <Agrandi>
              <Extincteur />
            </Agrandi>
            <Agrandi relatif={1.85}>
              <PorteCoupeFeu />
            </Agrandi>
          </span>
        </div>
      </div>
      <SolDeSalle />
      {deplie && <DetailDeTessera ecran={deplie} salle={deplie === "journal" ? (detaillee ?? salle) : salle} onFermer={fermer} />}
    </article>
  );
}
