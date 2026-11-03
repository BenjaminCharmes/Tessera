import { useMemo, useState, type RefObject } from "react";
import { useResource } from "../../hooks/useResource";
import { filtrerFichiers, listerFichiers } from "../../lib/indexFichiers";
import { lireRecents } from "../../lib/fichiersRecents";
import { Resultats, SectionRecents, SectionTouches } from "./Sections";
import { useFichiersTouches } from "./touches";
import type { Project, Ticket } from "../../types/api";

interface EtatVideProps {
  project: Project;
  /** Le ticket dont on montre les fichiers touchés, ou null. */
  ticketTouche: Ticket | null;
  onOpenFile: (chemin: string) => void;
  /** Le champ de recherche — tenu par le parent, qui y met le focus (Ctrl+P). */
  champRef: RefObject<HTMLInputElement | null>;
}

/**
 * Ce que l'onglet Fichiers montre quand rien n'est ouvert — ticket-428 : de
 * quoi en ouvrir un. Une recherche par chemin, les fichiers du dernier run, et
 * les derniers ouverts.
 */
export default function EtatVide({
  project,
  ticketTouche,
  onOpenFile,
  champRef,
}: EtatVideProps) {
  const [requete, setRequete] = useState("");
  // Lus au montage : cette vue se remonte chaque fois qu'on referme un fichier.
  const [recents] = useState(() => lireRecents(project.id));
  const fetcher = useMemo(() => () => listerFichiers(project.path), [project.path]);
  const { data: index } = useResource<string[]>(fetcher, [], {
    projet: project.id,
    ressource: "index-fichiers",
  });
  const touches = useFichiersTouches(project.id, ticketTouche);
  const recherche = requete.trim() !== "";

  return (
    <div className="flex flex-1 justify-center overflow-auto px-8 py-12">
      <div className="flex w-full max-w-2xl flex-col gap-7">
        <div>
          <p className="text-lg font-semibold text-zinc-100">Aucun fichier ouvert</p>
          <p className="mt-1 text-sm text-zinc-400">
            Choisis un fichier dans l'arbre, ou cherche-le.
          </p>
        </div>
        <label className="block">
          <span className="sr-only">Rechercher un fichier</span>
          <input
            ref={champRef}
            type="text"
            value={requete}
            onChange={(e) => setRequete(e.target.value)}
            placeholder={`Rechercher un fichier dans ${project.name}…   Ctrl+P`}
            className="h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-200 placeholder:text-zinc-500"
          />
        </label>
        {recherche ? (
          <Resultats
            racine={project.path}
            chemins={filtrerFichiers(index, project.path, requete)}
            onOpen={onOpenFile}
          />
        ) : (
          <>
            <SectionTouches
              racine={project.path}
              ticketId={ticketTouche?.id ?? null}
              fichiers={touches.fichiers}
              erreur={touches.erreur}
              onOpen={onOpenFile}
            />
            <SectionRecents
              racine={project.path}
              chemins={recents}
              onOpen={onOpenFile}
            />
          </>
        )}
      </div>
    </div>
  );
}
