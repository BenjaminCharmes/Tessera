import { useEffect, useState } from "react";
import { IconChevronDown, IconChevronRight } from "../../design/icons";
import { listEntries, type DirEntry } from "../../lib/fs";

/**
 * Arbre de fichiers en lecture seule (ticket-065).
 *
 * Il sert à **naviguer**, pas à travailler : ouvrir un fichier pour le lire,
 * pas pour l'éditer. Le pivot cockpit assume que l'édition se fait dans VSCode,
 * donc rien ici ne cherche à rivaliser avec un explorateur d'IDE — ni menu
 * contextuel, ni glisser-déposer, ni renommage.
 *
 * Le chargement est **paresseux** : un dépôt client peut contenir des dizaines
 * de milliers de fichiers, et n'en lire la liste qu'à l'ouverture d'un dossier
 * est ce qui garde l'arbre utilisable dessus.
 */
interface FileTreeProps {
  racine: string;
  onSelectFile: (path: string) => void;
  fichierActif?: string | null;
}

export default function FileTree({
  racine,
  onSelectFile,
  fichierActif = null,
}: FileTreeProps) {
  return (
    <div className="h-full overflow-auto py-1 text-sm">
      <Dossier
        chemin={racine}
        profondeur={0}
        onSelectFile={onSelectFile}
        fichierActif={fichierActif}
      />
    </div>
  );
}

interface DossierProps {
  chemin: string;
  profondeur: number;
  onSelectFile: (path: string) => void;
  fichierActif: string | null;
}

function Dossier({
  chemin,
  profondeur,
  onSelectFile,
  fichierActif,
}: DossierProps) {
  const [entrees, setEntrees] = useState<DirEntry[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [ouverts, setOuverts] = useState<Set<string>>(new Set());

  useEffect(() => {
    let annule = false;
    void (async () => {
      try {
        const e = await listEntries(chemin);
        if (!annule) setEntrees(e);
      } catch (err: unknown) {
        if (!annule) setErreur(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      annule = true;
    };
  }, [chemin]);

  if (erreur) {
    return (
      <p className="px-3 py-1.5 text-xs text-red-400">
        Impossible de lire ce dossier : {erreur}
      </p>
    );
  }

  if (entrees === null) {
    return <p className="px-3 py-1.5 text-xs text-zinc-500">chargement…</p>;
  }

  return (
    <ul>
      {entrees.map((entree) => {
        const ouvert = ouverts.has(entree.path);
        const actif = entree.path === fichierActif;
        return (
          <li key={entree.path}>
            <button
              type="button"
              onClick={() => {
                if (entree.is_dir) {
                  setOuverts((prec) => {
                    const suivant = new Set(prec);
                    if (suivant.has(entree.path)) suivant.delete(entree.path);
                    else suivant.add(entree.path);
                    return suivant;
                  });
                } else {
                  onSelectFile(entree.path);
                }
              }}
              className={`flex w-full items-center gap-1.5 py-0.5 pr-2 text-left transition-colors ${
                actif
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
              }`}
              style={{ paddingLeft: `${8 + profondeur * 12}px` }}
            >
              <span className="flex w-3 shrink-0 justify-center text-zinc-600">
                {entree.is_dir ? (
                  ouvert ? (
                    <IconChevronDown size={12} />
                  ) : (
                    <IconChevronRight size={12} />
                  )
                ) : null}
              </span>
              <span className="truncate">{entree.name}</span>
            </button>
            {entree.is_dir && ouvert && (
              <Dossier
                chemin={entree.path}
                profondeur={profondeur + 1}
                onSelectFile={onSelectFile}
                fichierActif={fichierActif}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}
