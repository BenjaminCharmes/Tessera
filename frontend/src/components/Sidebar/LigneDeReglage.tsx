import { useState } from "react";
import type { Reglage } from "../../lib/apiReglages";

/** Ce qui s'applique quand : le texte que le panneau dit en clair. */
const EFFETS: Record<string, string> = {
  run_max_budget_usd: "au prochain run",
  llm_max_budget_usd: "au prochain run",
  dialogue_timeout_s: "au prochain run",
  max_parallel_test_runs: "dès la prochaine suite de tests",
  keep_awake_during_runs: "à l'ouverture du prochain premier run",
};

function dire(valeur: number | boolean): string {
  return typeof valeur === "boolean" ? (valeur ? "oui" : "non") : String(valeur);
}

interface LigneProps {
  reglage: Reglage;
  onEcrire: (nom: string, valeur: number | boolean) => Promise<string | null>;
  onRetirer: (nom: string) => Promise<string | null>;
}

/** Un réglage : libellé, champ, défaut de `.env`, effet, et ses deux gestes. */
export default function LigneDeReglage({ reglage, onEcrire, onRetirer }: LigneProps) {
  const [brouillon, setBrouillon] = useState<string>(String(reglage.valeur));
  const [coche, setCoche] = useState<boolean>(reglage.valeur === true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const { nom, libelle, type, minimum, maximum } = reglage;
  const identifiant = `reglage-${nom}`;

  const nombre = Number(brouillon);
  // Un zéro, un nombre hors bornes ou illisible n'est jamais offert : l'API le refuserait.
  const valide =
    type === "bool" ||
    (brouillon.trim() !== "" &&
      Number.isFinite(nombre) &&
      (minimum === null || nombre >= minimum) &&
      (maximum === null || nombre <= maximum) &&
      (type !== "int" || Number.isInteger(nombre)));

  async function agir(action: () => Promise<string | null>) {
    setOccupe(true);
    const echec = await action();
    setErreur(echec);
    setOccupe(false);
  }

  return (
    <li className="border-b border-zinc-800 px-3 py-2.5 last:border-b-0">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={identifiant} className="text-xs text-zinc-200">
          {libelle}
        </label>
        {type === "bool" ? (
          <input
            id={identifiant}
            type="checkbox"
            checked={coche}
            onChange={(e) => setCoche(e.target.checked)}
          />
        ) : (
          <input
            id={identifiant}
            type="number"
            value={brouillon}
            min={minimum ?? undefined}
            max={maximum ?? undefined}
            step={type === "int" ? 1 : "any"}
            onChange={(e) => setBrouillon(e.target.value)}
            className="w-20 rounded-md border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-xs text-zinc-100"
          />
        )}
      </div>
      <p className="mt-1 text-micro text-zinc-500">
        Défaut de .env : {dire(reglage.defaut)}
        {minimum !== null && maximum !== null ? ` · entre ${minimum} et ${maximum}` : ""}
        {` · ${EFFETS[nom] ?? "au prochain run"}`}
      </p>
      {reglage.runs_ouverts > 0 ? (
        <p className="mt-1 text-micro text-amber-400">
          {reglage.runs_ouverts} run{reglage.runs_ouverts > 1 ? "s" : ""} gardent l'ancienne valeur
        </p>
      ) : null}
      <div className="mt-1.5 flex gap-1.5">
        <button
          type="button"
          disabled={!valide || occupe}
          onClick={() => agir(() => onEcrire(nom, type === "bool" ? coche : nombre))}
          className="rounded-md bg-violet-500/15 px-2 py-1 text-micro text-zinc-100 ring-1 ring-inset ring-violet-500/40 hover:bg-violet-500/25 disabled:opacity-40"
        >
          Appliquer
        </button>
        {reglage.modifie ? (
          <button
            type="button"
            disabled={occupe}
            onClick={() => agir(() => onRetirer(nom))}
            className="rounded-md px-2 py-1 text-micro text-zinc-300 ring-1 ring-inset ring-zinc-700 hover:bg-zinc-800 disabled:opacity-40"
          >
            Revenir au défaut
          </button>
        ) : null}
      </div>
      {erreur ? (
        <p role="alert" className="mt-1 text-micro text-red-400">
          {erreur}
        </p>
      ) : null}
    </li>
  );
}
