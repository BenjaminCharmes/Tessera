import { useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type { PipelineReglages, PipelineReglagesPatch } from "../../types/api";

/**
 * Régler le pipeline d'un projet sans ouvrir `agents.json` — ticket-196.
 *
 * Chaque interrupteur dit ce qu'il coûte : un appel LLM de plus par tour pour
 * la sécurité et le validateur, une commande lancée depuis le dossier du
 * projet pour le testeur. `merge` demande confirmation : merger, c'est
 * décider qu'un travail est bon (ADR-029, ADR-045).
 *
 * En lecture seule pendant un run : la politique est lue une fois avant le
 * premier agent (ADR-027), un changement ne vaudrait qu'au run suivant.
 */
interface PanneauPipelineProps {
  projectId: string;
  runEnCours: boolean;
}

const CHAMP =
  "rounded-sm border border-zinc-700 bg-zinc-950 px-1.5 py-0.5 text-micro text-zinc-200 outline-hidden focus:border-zinc-500 disabled:opacity-50";

export default function PanneauPipeline({ projectId, runEnCours }: PanneauPipelineProps) {
  const fetcher = useMemo(() => () => api.pipeline.get(projectId), [projectId]);
  const charge = useResource<PipelineReglages | null>(fetcher, null);
  const [modifie, setModifie] = useState<{ projectId: string; data: PipelineReglages } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirmerMerge, setConfirmerMerge] = useState(false);
  const [commande, setCommande] = useState<string | null>(null);

  const data = modifie?.projectId === projectId ? modifie.data : charge.data;
  if (!data) return null;
  const lectureSeule = runEnCours;

  async function enregistrer(patch: PipelineReglagesPatch) {
    setMessage(null);
    try {
      setModifie({ projectId, data: await api.pipeline.set(projectId, patch) });
      setMessage("Enregistré. Il s'applique au prochain run.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  function changerAutonomie(valeur: string) {
    if (valeur === "merge") {
      setConfirmerMerge(true);
      return;
    }
    setConfirmerMerge(false);
    void enregistrer({ autonomy: valeur });
  }

  const testCommand = commande ?? data.test_command ?? "";

  return (
    <div className="flex flex-col gap-2 border-b border-zinc-800 px-3 py-2 text-micro text-zinc-300">
      {lectureSeule && (
        <p className="text-zinc-500">
          Un run est en cours : les réglages s'appliqueront au run suivant.
        </p>
      )}

      <Ligne
        label="Sécurité"
        cout="un appel LLM de plus par tour"
        checked={data.securite_enabled}
        disabled={lectureSeule}
        onChange={(v) => void enregistrer({ securite_enabled: v })}
      />
      <Ligne
        label="Validateur"
        cout="un appel LLM de plus par tour"
        checked={data.validateur_enabled}
        disabled={lectureSeule}
        onChange={(v) => void enregistrer({ validateur_enabled: v })}
      />
      <Ligne
        label="Testeur"
        cout="lance la commande depuis le dossier du projet, sans shell"
        checked={data.testeur_enabled}
        disabled={lectureSeule || !testCommand.trim()}
        onChange={(v) => void enregistrer({ testeur_enabled: v, test_command: testCommand })}
      />
      <label className="flex items-center gap-2">
        <span className="w-24 shrink-0 text-zinc-400">Commande de test</span>
        <input
          type="text"
          aria-label="Commande de test"
          value={testCommand}
          disabled={lectureSeule}
          placeholder="npm run test -- --run"
          onChange={(e) => setCommande(e.target.value)}
          onBlur={() => {
            if (commande !== null && commande !== (data.test_command ?? "")) {
              void enregistrer({ test_command: commande.trim() || null });
            }
          }}
          className={`${CHAMP} flex-1`}
        />
      </label>
      <label className="flex items-center gap-2">
        <span className="w-24 shrink-0 text-zinc-400">Tours de revue</span>
        <input
          type="number"
          aria-label="Tours de revue"
          min={1}
          max={10}
          value={data.max_review_rounds}
          disabled={lectureSeule}
          onChange={(e) => void enregistrer({ max_review_rounds: Number(e.target.value) })}
          className={`${CHAMP} w-16`}
        />
      </label>
      <label className="flex items-center gap-2">
        <span className="w-24 shrink-0 text-zinc-400">Autonomie</span>
        <select
          aria-label="Autonomie"
          value={confirmerMerge ? "merge" : data.autonomy}
          disabled={lectureSeule}
          onChange={(e) => changerAutonomie(e.target.value)}
          className={CHAMP}
        >
          <option value="commit">commit — le travail reste sur sa branche</option>
          <option value="pr">pr — pousse et ouvre la PR</option>
          <option value="merge">merge — merge si la CI est verte</option>
        </select>
      </label>
      {confirmerMerge && (
        <div role="alert" className="rounded-sm border border-amber-900/60 bg-amber-950/30 px-2 py-1.5 text-amber-100">
          <p>
            Merger, c'est décider qu'un travail est bon. À ce niveau, plus rien
            d'humain ne s'interpose entre l'approbation du pipeline et la branche
            de base (ADR-029, ADR-045).
          </p>
          <div className="mt-1 flex gap-2">
            <button
              type="button"
              onClick={() => {
                setConfirmerMerge(false);
                void enregistrer({ autonomy: "merge" });
              }}
              className="rounded-sm bg-amber-500/20 px-2 py-0.5 text-amber-100 hover:bg-amber-500/30"
            >
              Confirmer merge
            </button>
            <button
              type="button"
              onClick={() => setConfirmerMerge(false)}
              className="text-zinc-400 hover:text-zinc-200"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
      {data.autonomy === "merge" && (
        <Ligne
          label="Merger sans CI"
          cout="sur le seul verdict du pipeline (ADR-045)"
          checked={data.merge_without_ci}
          disabled={lectureSeule}
          onChange={(v) => void enregistrer({ merge_without_ci: v })}
        />
      )}
      {message && <p className="text-zinc-500">{message}</p>}
    </div>
  );
}

function Ligne({
  label,
  cout,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  cout: string;
  checked: boolean;
  disabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="w-24 shrink-0 text-zinc-300">{label}</span>
      <span className="text-zinc-500">{cout}</span>
    </label>
  );
}
