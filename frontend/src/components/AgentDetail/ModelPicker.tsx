import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { ProjectAgents } from "../../types/api";

/**
 * Le modèle qu'utilise cet agent **sur ce projet** — ticket-080.
 *
 * Le modèle est une propriété du projet, pas de l'agent : le même `codeur`
 * mérite un modèle lourd sur un backend métier et un modèle léger sur un
 * script personnel. C'est pourquoi le réglage vit dans le `agents.json` du
 * projet, et non dans le registre d'agents, qui est global.
 *
 * Seuls les modèles dont l'application sait calculer le coût sont proposés :
 * en choisir un hors grille fausserait la ventilation des dépenses, qui est
 * justement ce sur quoi on s'appuie pour décider où descendre en gamme.
 *
 * Le composant se tait si le projet ne déclare pas cet agent — il n'y a alors
 * rien à régler.
 */
interface ModelPickerProps {
  projectId: string;
  role: string;
}

export default function ModelPicker({ projectId, role }: ModelPickerProps) {
  const [data, setData] = useState<ProjectAgents | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let annule = false;
    setData(null);
    setMessage(null);
    void (async () => {
      try {
        const d = await api.git.agents(projectId);
        if (!annule) setData(d);
      } catch {
        if (!annule) setData(null);
      }
    })();
    return () => {
      annule = true;
    };
  }, [projectId, role]);

  const config = data?.agents.find((a) => a.role === role);
  if (!data || !config) return null;

  async function changer(model: string) {
    setMessage(null);
    try {
      setData(await api.git.setAgentModel(projectId, role, model));
      setMessage("Enregistré. Il s'applique au prochain appel.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 px-4 py-2">
      <label htmlFor="modele-agent" className="text-mini text-zinc-400">
        Modèle sur ce projet
      </label>
      <select
        id="modele-agent"
        value={config.model}
        onChange={(e) => void changer(e.target.value)}
        className="rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-mini text-zinc-200 outline-hidden focus:border-zinc-500"
      >
        {data.known_models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {message && <span className="text-micro text-zinc-500">{message}</span>}
    </div>
  );
}
