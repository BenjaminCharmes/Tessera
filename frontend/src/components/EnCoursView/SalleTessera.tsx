import { useMemo } from "react";
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
import BaieAvecFiche from "./BaieAvecFiche";
import EcransDeTessera from "./EcransDeTessera";
import SolDeSalle from "./SolDeSalle";
import { formaterHeure, formaterMo } from "./format";

interface SalleTesseraProps {
  /** Le nom affiché du projet bootstrap, lu dans la vue d'ensemble. */
  nom: string;
  /** Heure de la dernière lecture de l'inventaire : elle relance la lecture de la salle. */
  lueA: number;
}

/** Un processus de Tessera vu comme une app, pour la fiche partagée avec les autres salles. */
function commeUneApp(p: ProcessusDeTessera): AppEnCours {
  return {
    project_id: "ide-core", project_name: "Tessera", nom: p.nom, origine: "externe",
    pid: p.pid ?? 0, ports: [p.port], demarre_a: p.demarre_a, memoire_mo: p.memoire_mo,
  };
}

/** « ven. 14:00 » : la remise à zéro tombe souvent un autre jour que celui qu'on regarde. */
function remiseAZero(iso: string | null): string {
  const t = iso === null ? Number.NaN : Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  return new Date(t).toLocaleString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

function Compteur({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <div className="min-w-36 rounded-sm border-[3px] border-zinc-800 bg-zinc-700 px-2.5 py-1.5 font-mono text-micro text-zinc-200">
      <div className="text-zinc-400">{titre}</div>
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
  const semaine = useQuotaLu(lueA)?.["seven_day"];
  if (salle === null) return null;

  const memoire = salle.processus.reduce((s, p) => s + p.memoire_mo, 0);
  const debut = salle.processus.find((p) => p.nom === "backend")?.demarre_a ?? null;
  const refroidi = salle.ollama.refroidissement_s !== null;
  return (
    <article aria-label="Salle Tessera" data-salle-tessera className="mb-4 overflow-hidden rounded-lg border border-violet-800 bg-(--sprite-salle-mur)">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-zinc-800 bg-zinc-900/60 px-3 py-2">
        <span aria-hidden="true" className="size-2.5 rounded-[2px] bg-violet-500" />
        <h3 className="text-sm font-semibold text-zinc-100">{nom}</h3>
        <span className="text-xs text-zinc-400">
          {salle.processus.length} services · {formaterMo(memoire)} · démarré à {formaterHeure(debut)}
        </span>
        <span className="rounded-full bg-violet-950 px-2.5 py-0.5 text-micro text-zinc-200 ring-1 ring-violet-700">fait tourner l'IDE</span>
      </header>
      <div className="relative px-6 pt-10">
        <div className="absolute inset-x-0 top-0">
          <CheminDeCables />
        </div>
        <EcransDeTessera salle={salle} />
        <div className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b-4 border-(--sprite-salle-plinthe)">
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
          <span className="flex flex-wrap items-end gap-3 pb-1.5">
            <Compteur titre="QUOTA DE LA SEMAINE">
              {semaine ? (
                <>
                  <div className="my-1 h-2 bg-zinc-900">
                    <div className={`h-2 ${semaine.utilization >= 0.85 ? "bg-amber-400" : "bg-blue-400"}`} style={{ width: `${Math.round(semaine.utilization * 100)}%` }} />
                  </div>
                  <div>{Math.round(semaine.utilization * 100)} % · remis à zéro {remiseAZero(semaine.resets_at)}</div>
                </>
              ) : (
                <div>pas encore relevé</div>
              )}
            </Compteur>
            <Compteur titre="BASE · WORKTREES">
              <div>tessera.db {formaterMo(salle.base_mo)}</div>
              <div>{salle.worktrees} worktree{salle.worktrees > 1 ? "s" : ""} ouvert{salle.worktrees > 1 ? "s" : ""}</div>
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
            <Agrandi relatif={2}>
              <PorteCoupeFeu />
            </Agrandi>
          </span>
        </div>
      </div>
      <SolDeSalle />
    </article>
  );
}
