import { useMemo, useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import type {
  AgentSettingsPatch,
  FallbackConfig,
  ProjectAgents,
} from "../../types/api";

/**
 * Le provider, le modèle et le repli qu'utilise cet agent **sur ce projet**
 * — ticket-080 pour le modèle, ticket-188 pour le reste.
 *
 * Le modèle est une propriété du projet, pas de l'agent : le même `codeur`
 * mérite un modèle lourd sur un backend métier et un modèle léger sur un
 * script personnel. C'est pourquoi le réglage vit dans le `agents.json` du
 * projet, et non dans le registre d'agents, qui est global.
 *
 * Sur un provider Anthropic, seuls les modèles dont l'application sait
 * calculer le coût sont proposés : en choisir un hors grille fausserait la
 * ventilation des dépenses. Sur un autre provider le nom est libre, et se
 * saisit.
 *
 * Le repli est explicite : un provider absent d'une machine ne doit pas
 * rendre le manifeste inutilisable ailleurs, et un repli utilisé se voit.
 *
 * Le composant se tait si le projet ne déclare pas cet agent — il n'y a alors
 * rien à régler.
 */
interface ModelPickerProps {
  projectId: string;
  role: string;
}

const CHAMP =
  "rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-mini text-zinc-200 outline-hidden focus:border-zinc-500";

export default function ModelPicker({ projectId, role }: ModelPickerProps) {
  // La lecture est par projet, pas par agent : changer d'agent ne relit rien.
  const fetcher = useMemo(() => () => api.git.agents(projectId), [projectId]);
  const charge = useResource<ProjectAgents | null>(fetcher, null);
  // Ce que le dernier enregistrement a rendu, s'il porte sur ce projet ; le
  // message est clé de la même façon pour disparaître au changement d'agent
  // sans `setState` dans un effet (ticket-123).
  const cle = `${projectId}/${role}`;
  const [modifie, setModifie] = useState<{
    projectId: string;
    data: ProjectAgents;
  } | null>(null);
  const [message, setMessage] = useState<{ cle: string; texte: string } | null>(
    null,
  );

  const data = modifie?.projectId === projectId ? modifie.data : charge.data;
  const config = data?.agents.find((a) => a.role === role);
  if (!data || !config) return null;

  const modelesDe = (provider: string): string[] =>
    data.known_models_by_provider[provider] ?? [];

  async function enregistrer(patch: AgentSettingsPatch) {
    setMessage(null);
    try {
      setModifie({
        projectId,
        data: await api.git.setAgentModel(projectId, role, patch),
      });
      setMessage({ cle, texte: "Enregistré. Il s'applique au prochain appel." });
    } catch (err: unknown) {
      setMessage({
        cle,
        texte: err instanceof Error ? err.message : String(err),
      });
    }
  }

  function changerProvider(provider: string) {
    // Un modèle hors grille serait refusé sur un provider Anthropic : on
    // bascule sur le premier proposable plutôt que d'envoyer un 422.
    const liste = modelesDe(provider);
    const model =
      liste.length > 0 && !liste.includes(config!.model) ? liste[0] : config!.model;
    void enregistrer({ model, provider });
  }

  function changerRepli(fallback: FallbackConfig | null) {
    void enregistrer({ model: config!.model, fallback });
  }

  const repli = config.fallback;
  const premierModele = (provider: string): string => modelesDe(provider)[0] ?? "";

  return (
    <div className="flex flex-col gap-2 border-b border-zinc-800 px-4 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="provider-agent" className="text-mini text-zinc-400">
          Provider sur ce projet
        </label>
        <select
          id="provider-agent"
          value={config.provider}
          onChange={(e) => changerProvider(e.target.value)}
          className={CHAMP}
        >
          {data.known_providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <label htmlFor="modele-agent" className="text-mini text-zinc-400">
          Modèle sur ce projet
        </label>
        <ChoixDeModele
          id="modele-agent"
          valeur={config.model}
          propositions={modelesDe(config.provider)}
          onChange={(model) => void enregistrer({ model })}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1 text-mini text-zinc-400">
          <input
            type="checkbox"
            checked={repli !== null}
            onChange={(e) =>
              changerRepli(
                e.target.checked
                  ? {
                      provider: data.known_providers[0] ?? "agent_sdk",
                      model: premierModele(data.known_providers[0] ?? "agent_sdk"),
                    }
                  : null,
              )
            }
          />
          Repli si indisponible
        </label>
        {repli && (
          <>
            <label htmlFor="provider-repli" className="text-mini text-zinc-400">
              Provider de repli
            </label>
            <select
              id="provider-repli"
              value={repli.provider}
              onChange={(e) => {
                const provider = e.target.value;
                const liste = modelesDe(provider);
                const model =
                  liste.length > 0 && !liste.includes(repli.model)
                    ? liste[0]
                    : repli.model;
                changerRepli({ provider, model });
              }}
              className={CHAMP}
            >
              {data.known_providers.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <label htmlFor="modele-repli" className="text-mini text-zinc-400">
              Modèle de repli
            </label>
            <ChoixDeModele
              id="modele-repli"
              valeur={repli.model}
              propositions={modelesDe(repli.provider)}
              onChange={(model) => changerRepli({ provider: repli.provider, model })}
            />
          </>
        )}
      </div>
      {message?.cle === cle && (
        <span className="text-micro text-zinc-500">{message.texte}</span>
      )}
    </div>
  );
}

/** Une liste quand le provider en propose une, une saisie libre sinon. */
function ChoixDeModele({
  id,
  valeur,
  propositions,
  onChange,
}: {
  id: string;
  valeur: string;
  propositions: string[];
  onChange: (model: string) => void;
}) {
  if (propositions.length > 0) {
    return (
      <select
        id={id}
        value={valeur}
        onChange={(e) => onChange(e.target.value)}
        className={CHAMP}
      >
        {propositions.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }
  return (
    <input
      id={id}
      type="text"
      defaultValue={valeur}
      onBlur={(e) => {
        if (e.target.value.trim() && e.target.value !== valeur) {
          onChange(e.target.value.trim());
        }
      }}
      className={CHAMP}
    />
  );
}
