import type { Rituel } from "../../lib/apiRituels";
import type { Project } from "../../types/api";
import type { UseRituelsResult } from "../../hooks/useRituels";
import RegionTitle from "../../design/RegionTitle";
import CarteRituel from "./CarteRituel";
import { libelleDeDate, libelleDuRythme } from "./format";

interface RituelsViewProps {
  rituels: UseRituelsResult;
  projets: Project[];
  onOpenProject?: (p: Project) => void;
}

function Section({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <section aria-label={titre} className="mb-6">
      <h2 className="mb-2">
        <RegionTitle taille="sm">{titre}</RegionTitle>
      </h2>
      {children}
    </section>
  );
}

function LigneSimple({ rituel, quand }: { rituel: Rituel; quand: string }) {
  return (
    <li className="flex items-baseline justify-between gap-3 border-b border-zinc-800 py-1.5 text-sm">
      <span className="text-zinc-200">
        {rituel.titre} <span className="text-xs text-zinc-500">{libelleDuRythme(rituel.rythme)}</span>
      </span>
      <span className="text-xs text-zinc-400">{quand}</span>
    </li>
  );
}

const parDate = (cle: "prochaine" | "fait_le", sens: 1 | -1) => (a: Rituel, b: Rituel) =>
  sens * (a[cle] ?? "").localeCompare(b[cle] ?? "");

/** La vue Rituels : ce qui est en retard, ce qui vient, ce qui est fait (ticket-903). */
export default function RituelsView({ rituels, projets, onOpenProject }: RituelsViewProps) {
  const { rituels: liste, erreur, synchro, fait, reporter } = rituels;
  const aFaire = liste.filter((r) => r.statut === "en_retard");
  const aVenir = liste.filter((r) => r.statut === "a_venir").sort(parDate("prochaine", 1));
  const faits = liste.filter((r) => r.statut === "fait").sort(parDate("fait_le", -1));

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="mb-4">
        <RegionTitle>Rituels</RegionTitle>
      </h2>
      {synchro === "locale" ? (
        <p className="-mt-3 mb-4 text-xs text-zinc-500">
          État gardé sur ce PC seulement : la synchronisation GitHub n'est pas active.
        </p>
      ) : null}
      {erreur ? (
        <p role="alert" className="mb-4 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
          {erreur}
        </p>
      ) : null}
      <Section titre="À faire">
        {aFaire.length === 0 ? (
          <p className="text-sm text-zinc-500">Rien en retard.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {aFaire.map((r) => (
              <CarteRituel
                key={r.id}
                rituel={r}
                projets={projets}
                onOpenProject={onOpenProject}
                onFait={(id) => void fait(id)}
                onReporter={(id) => void reporter(id)}
              />
            ))}
          </ul>
        )}
      </Section>
      <Section titre="À venir">
        <ul>
          {aVenir.map((r) => (
            <LigneSimple key={r.id} rituel={r} quand={libelleDeDate(r.prochaine)} />
          ))}
        </ul>
      </Section>
      <Section titre="Faits récemment">
        <ul>
          {faits.map((r) => (
            <LigneSimple key={r.id} rituel={r} quand={libelleDeDate(r.fait_le)} />
          ))}
        </ul>
      </Section>
    </div>
  );
}
