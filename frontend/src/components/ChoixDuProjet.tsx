import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import type { Project } from "../types/projets";
import type { ProjectOverview } from "../types/api";
import { titreEtSousTitre } from "../lib/titreDuProjet";
import IconeDuProjet from "./ProjetsView/IconeDuProjet";

const AUCUN: ProjectOverview[] = [];
const lireLesApercus = () => api.projects.overview();

interface ChoixDuProjetProps {
  /** Le nom de la vue qui attend un projet : « les tickets », « l'historique »… */
  vue: string;
  projets: readonly Project[];
  onSelectProject: (p: Project) => void;
}

/**
 * Une vue de projet sans projet choisi — ticket-735. Avant, Tickets, Fichiers,
 * Historique, Agents et Chat s'ouvraient sur des coquilles vides (« Aucun run sur
 * ce projet », « Chargement… »). L'écran dit ce qui manque et propose les projets.
 */
export default function ChoixDuProjet({ vue, projets, onSelectProject }: ChoixDuProjetProps) {
  const tries = [...projets].sort((a, b) => a.name.localeCompare(b.name, "fr"));
  // Les icônes viennent des aperçus ; tant qu'ils ne sont pas lus, l'initiale tient la place.
  const { data: apercus } = useResource(lireLesApercus, AUCUN);
  const iconeDe = (id: string) => apercus.find((a) => a.id === id)?.icon ?? false;
  return (
    <section
      aria-labelledby="choix-du-projet"
      className="flex h-full min-h-0 flex-col items-center overflow-y-auto px-6 py-12"
    >
      <div className="flex max-w-xl flex-col items-center gap-2 text-center">
        <h2 id="choix-du-projet" className="text-xl font-semibold tracking-tight text-zinc-50">
          Sur quel projet travailles-tu ?
        </h2>
        <p className="text-sm leading-relaxed text-zinc-400">
          Choisis un projet pour {vue.startsWith("discuter") ? vue : `voir ${vue}`}. Tessera le gardera la prochaine fois.
        </p>
      </div>
      <ul className="mt-8 grid w-full max-w-5xl grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {tries.map((p) => {
          const { titre, sousTitre } = titreEtSousTitre(p.name);
          return (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onSelectProject(p)}
                className="flex h-full w-full items-start gap-3 rounded-xl border border-zinc-800/80 bg-zinc-900/70 p-4 text-left shadow-sm shadow-black/30 hover:border-zinc-700 hover:bg-zinc-800/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
              >
                <IconeDuProjet projet={{ id: p.id, name: p.name, icon: iconeDe(p.id) }} taille="tuile" />
                <span className="flex min-w-0 flex-col gap-1">
                  <span className="font-semibold text-zinc-100">{titre}</span>
                  {sousTitre ? <span className="text-xs text-zinc-400">{sousTitre}</span> : null}
                  {p.description ? (
                    <span className="mt-1 line-clamp-2 text-xs leading-relaxed text-zinc-500">{p.description}</span>
                  ) : null}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
