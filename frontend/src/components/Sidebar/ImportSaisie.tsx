import InfoTip from "../../design/InfoTip";
import type { ImportMode, SourceType } from "./importValidation";

const CHAMP =
  "w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400";

export interface SaisieProps {
  sourceType: SourceType;
  sourcePath: string;
  mode: ImportMode;
  repoUrl: string;
  inputError: string | null;
  apiError: string | null;
  onSourceType: (value: SourceType) => void;
  onSourcePath: (value: string) => void;
  onMode: (value: ImportMode) => void;
  onRepoUrl: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onClose: () => void;
}

function Erreur({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-xs text-red-400" role="alert">
      {message}
    </p>
  );
}

function BoutonSource(props: {
  actif: boolean;
  libelle: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className={`flex-1 py-1.5 text-xs transition-colors ${
        props.actif
          ? "bg-zinc-700 text-zinc-100"
          : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
      }`}
      aria-pressed={props.actif}
    >
      {props.libelle}
    </button>
  );
}

function ChoixDuMode(props: {
  mode: ImportMode;
  onMode: (value: ImportMode) => void;
}) {
  const options: { valeur: ImportMode; libelle: string }[] = [
    { valeur: "symlink", libelle: "Symlink (recommandé)" },
    { valeur: "copy", libelle: "Copie" },
  ];
  return (
    <fieldset>
      <legend className="text-xs text-zinc-400 mb-2">Mode</legend>
      <div className="flex gap-4">
        {options.map((o) => (
          <label
            key={o.valeur}
            className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer"
          >
            <input
              type="radio"
              name="import-mode"
              value={o.valeur}
              checked={props.mode === o.valeur}
              onChange={() => props.onMode(o.valeur)}
              className="accent-zinc-400"
            />
            {o.libelle}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function ChampLocal(props: SaisieProps) {
  return (
    <>
      <div>
        <label htmlFor="import-path" className="block text-xs text-zinc-400 mb-1">
          Chemin du dossier <span className="text-red-400">*</span>
        </label>
        <input
          id="import-path"
          type="text"
          value={props.sourcePath}
          onChange={(e) => props.onSourcePath(e.target.value)}
          placeholder="/Users/vous/Desktop/mon-projet"
          className={CHAMP}
          autoFocus
        />
        <Erreur message={props.inputError} />
      </div>
      <ChoixDuMode mode={props.mode} onMode={props.onMode} />
    </>
  );
}

function ChampGithub(props: SaisieProps) {
  return (
    <div>
      {/* L'icône reste hors du <label> : dedans, le bouton
          prendrait le libellé du champ (ticket-273). */}
      <div className="mb-1 flex items-center gap-1">
        <label htmlFor="github-url" className="text-xs text-zinc-400">
          URL du repo GitHub <span className="text-red-400">*</span>
        </label>
        <InfoTip>
          Les repos privés nécessitent un token configuré dans les settings.
        </InfoTip>
      </div>
      <input
        id="github-url"
        type="url"
        value={props.repoUrl}
        onChange={(e) => props.onRepoUrl(e.target.value)}
        placeholder="https://github.com/owner/mon-repo"
        className={CHAMP}
        autoFocus
      />
      <Erreur message={props.inputError} />
    </div>
  );
}

/** Input step: source toggle, source fields, API error and actions. */
export default function ImportSaisie(props: SaisieProps) {
  const { sourceType } = props;
  return (
    <>
      <h2 className="text-zinc-100 text-base font-semibold">
        Importer un projet existant
      </h2>

      <div className="flex rounded-sm overflow-hidden border border-zinc-700">
        <BoutonSource
          actif={sourceType === "local"}
          libelle="Dossier local"
          onClick={() => props.onSourceType("local")}
        />
        <BoutonSource
          actif={sourceType === "github"}
          libelle="Cloner depuis GitHub"
          onClick={() => props.onSourceType("github")}
        />
      </div>

      <form
        onSubmit={props.onSubmit}
        noValidate
        className="flex flex-col gap-4"
      >
        {sourceType === "local" ? (
          <ChampLocal {...props} />
        ) : (
          <ChampGithub {...props} />
        )}

        {props.apiError && (
          <p className="text-xs text-red-400" role="alert">
            {props.apiError}
          </p>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={props.onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Annuler
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors flex items-center gap-2"
          >
            {sourceType === "local" ? "Importer" : "Cloner"}
          </button>
        </div>
      </form>
    </>
  );
}
