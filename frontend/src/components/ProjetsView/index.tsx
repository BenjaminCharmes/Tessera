import { useState } from "react";
import { api } from "../../lib/api";
import { notifierProjetsModifies } from "../../hooks/useProjects";
import { useEtatPersistant } from "../../hooks/useEtatPersistant";
import { useResource } from "../../hooks/useResource";
import type { Project, ProjectOverview, RunActif } from "../../types/api";
import { grouperParCategorie } from "../Sidebar/grouperParCategorie";
import EnTeteDeCategorie from "../Sidebar/EnTeteDeCategorie";
import { useCategoriesRepliees } from "../../hooks/useCategoriesRepliees";
import BarreProjets from "./BarreProjets";
import ProjetCarte from "./ProjetCarte";
import ModalesDeProjet, { type ModaleDeProjet } from "./ModalesDeProjet";
import {
  FILTRES_PAR_DEFAUT,
  SANS_CATEGORIE,
  estFiltresProjets,
  filtrerProjets,
  filtresActifs,
  pastillesDeCategories,
  trierProjets,
  type FiltresProjets,
} from "./organiser";

interface ProjetsViewProps {
  /** Les projets complets : la sélection rend un `Project`, pas une vue d'ensemble. */
  projets: Project[];
  activeProject: Project | null;
  onSelectProject: (project: Project) => void;
  /** Un projet vient d'être créé ou importé ; il devient le projet actif (ticket-586). */
  onProjectCreated?: (project: Project) => void;
  /** Les projets dont un run attend une réponse (ticket-186). */
  enAttente?: ReadonlySet<string>;
  /** Les runs vivants : une file en cours accepte des tickets depuis la carte (ticket-557). */
  runs?: RunActif[];
}

const AUCUN: ProjectOverview[] = [];
const lireVueDEnsemble = () => api.projects.overview();

const GRILLE = "grid gap-3 grid-cols-[repeat(auto-fill,minmax(18rem,1fr))]";

function Squelette() {
  return (
    <div className={`${GRILLE} p-4`} aria-label="Chargement des projets">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-40 animate-pulse rounded-sm bg-zinc-800" />
      ))}
    </div>
  );
}

function Message({ texte, action, onAction }: {
  texte: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center text-sm text-zinc-500">
      <p>{texte}</p>
      {action && (
        <button
          type="button"
          onClick={onAction}
          className="rounded-sm bg-zinc-700 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-600"
        >
          {action}
        </button>
      )}
    </div>
  );
}

/**
 * La vue Projets du centre : une carte par projet — ticket-399.
 *
 * La barre latérale reste la navigation rapide ; ici on choisit en voyant ce
 * qu'est chaque projet. La recherche, le filtre et le tri sont mémorisés comme
 * ceux du tableau : revenir sur l'onglet les retrouve.
 */
export default function ProjetsView({
  projets,
  activeProject,
  onSelectProject,
  onProjectCreated,
  enAttente,
  runs = [],
}: ProjetsViewProps) {
  const { data, loading, error, refresh } = useResource(lireVueDEnsemble, AUCUN);
  const [memorises, setFiltres] = useEtatPersistant<FiltresProjets>(
    "projets.vue",
    FILTRES_PAR_DEFAUT,
    estFiltresProjets,
  );
  const [echec, setEchec] = useState<string | null>(null);
  const [modale, setModale] = useState<ModaleDeProjet>(null);
  const { estRepliee, basculer } = useCategoriesRepliees();

  const pastilles = pastillesDeCategories(data);
  // Une catégorie mémorisée mais disparue (retirée depuis) ne doit pas vider la vue.
  const filtres: FiltresProjets =
    memorises.categorie !== null && !pastilles.some((p) => p.valeur === memorises.categorie)
      ? { ...memorises, categorie: null }
      : memorises;
  const categories = pastilles
    .filter((p) => p.valeur !== SANS_CATEGORIE)
    .map((p) => p.valeur);
  const visibles = trierProjets(filtrerProjets(data, filtres), filtres.tri);

  async function changerCategorie(projet: ProjectOverview, categorie: string) {
    setEchec(null);
    try {
      await api.projects.setCategory(projet.id, categorie);
      refresh();
      notifierProjetsModifies();
    } catch (e) {
      setEchec(e instanceof Error ? e.message : "Changement de catégorie impossible");
    }
  }

  // Le projet ajouté devient le projet actif, comme depuis l'ancienne liste.
  function projetAjoute(projet: Project) {
    refresh();
    notifierProjetsModifies();
    setModale(null);
    onProjectCreated?.(projet);
    onSelectProject(projet);
  }

  function carte(projet: ProjectOverview) {
    return (
      <ProjetCarte
        key={projet.id}
        projet={projet}
        actif={activeProject?.id === projet.id}
        enAttente={enAttente?.has(projet.id) ?? false}
        categories={categories}
        onSelect={() => {
          const complet = projets.find((p) => p.id === projet.id);
          if (complet) onSelectProject(complet);
        }}
        onChangerCategorie={(c) => void changerCategorie(projet, c)}
        onServicesChange={refresh}
        onFileLancee={refresh}
        fileEnCours={
          runs.find((r) => r.project_id === projet.id && r.mode === "queue")?.run_id ?? null
        }
      />
    );
  }

  let corps: React.ReactNode;
  if (error) {
    corps = <Message texte={error} action="Réessayer" onAction={refresh} />;
  } else if (loading && data.length === 0) {
    corps = <Squelette />;
  } else if (visibles.length === 0) {
    corps = filtresActifs(filtres) ? (
      <Message
        texte="Aucun projet ne correspond."
        action="Effacer la recherche"
        onAction={() => setFiltres({ ...filtres, recherche: "", categorie: null })}
      />
    ) : (
      <Message texte="Aucun projet pour l'instant." />
    );
  } else if (filtres.categorie !== null) {
    corps = <div className={`${GRILLE} p-4`}>{visibles.map(carte)}</div>;
  } else {
    corps = (
      <div className="flex flex-col gap-4 p-4">
        {grouperParCategorie(visibles).map((groupe) => {
          // Une recherche active montre ses résultats même dans une catégorie
          // repliée, sans toucher à l'état mémorisé (ticket-400).
          const repliee = estRepliee(groupe.categorie) && !filtres.recherche.trim();
          return (
            <section key={groupe.categorie ?? "__sans__"} className="flex flex-col gap-2">
              <h2>
                <EnTeteDeCategorie
                  categorie={groupe.categorie}
                  projets={groupe.projets}
                  repliee={repliee}
                  onBasculer={() => basculer(groupe.categorie)}
                />
              </h2>
              {!repliee && <div className={GRILLE}>{groupe.projets.map(carte)}</div>}
            </section>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <BarreProjets
        filtres={filtres}
        pastilles={pastilles}
        total={data.length}
        onChange={setFiltres}
        onImporter={() => setModale("import")}
        onCreer={() => setModale("creation")}
      />
      <ModalesDeProjet
        ouverte={modale}
        onFermer={() => setModale(null)}
        onAjoute={projetAjoute}
      />
      {echec && (
        <p role="alert" className="px-4 py-2 text-xs text-red-400">
          {echec}
        </p>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto">{corps}</div>
    </div>
  );
}
