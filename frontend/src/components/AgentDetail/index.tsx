import { useEffect, useState } from "react";
import MarkdownView from "../Editor/MarkdownView";
import { api } from "../../lib/api";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import type { AgentDetail as AgentDetailData } from "../../types/api";

/**
 * La définition d'un agent, au centre de l'écran (ticket-076).
 *
 * Le prompt système détermine tout le comportement d'un agent — c'est la
 * première chose à lire quand il se comporte mal. Il n'était visible nulle
 * part : la liste n'en montrait qu'un extrait, en infobulle au survol, et il
 * fallait ouvrir `agents/prompts/*.md` dans VSCode pour le connaître.
 *
 * Le rail dit *quel* agent, le centre montre *ce qu'il est*. C'est le même
 * partage que pour les tickets, et il ne valait pas pour cet onglet.
 */
interface AgentDetailProps {
  role: string | null;
}

export default function AgentDetail({ role }: AgentDetailProps) {
  const [detail, setDetail] = useState<AgentDetailData | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  // Les prompts natifs sont des fichiers Markdown ; les lire avec leurs `##`
  // et leurs `**` demande un effort que le contenu ne justifie pas
  // (ticket-078).
  const [vue, setVue] = useState<"rendu" | "source" | "edition">("rendu");
  const [brouillon, setBrouillon] = useState("");
  const [enregistrement, setEnregistrement] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
  if (!role) {
      setDetail(null);
      setErreur(null);
      return;
    }
    let annule = false;
    setDetail(null);
    setErreur(null);
    setVue("rendu");
    setMessage(null);
    void (async () => {
      try {
        const d = await api.agents.detail(role);
        if (!annule) {
          setDetail(d);
          setBrouillon(d.system_prompt);
        }
      } catch (err: unknown) {
        if (!annule) setErreur(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      annule = true;
    };
  }, [role]);

  async function enregistrer() {
    if (!role || !brouillon.trim()) {
      setMessage("Un prompt vide priverait l'agent de toute définition.");
      return;
    }
    setEnregistrement(true);
    setMessage(null);
    try {
      const d = await api.agents.updatePrompt(role, brouillon);
      setDetail(d);
      setMessage("Enregistré. Il s'applique au prochain appel de cet agent.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setEnregistrement(false);
    }
  }

  if (!role) {
    return (
      <div className="flex h-full flex-col bg-zinc-900">
        <div className={`${BAND} border-b border-zinc-700 px-4`}>
          <RegionTitle>Agent</RegionTitle>
        </div>
        <p className="px-4 py-3 text-xs text-zinc-500">
          Sélectionne un agent dans la liste pour lire sa définition.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>{role}</RegionTitle>
        {detail && (
          <div className="flex items-center gap-2">
            <div
              className="flex items-center gap-0.5"
              role="tablist"
              aria-label="Affichage du prompt"
            >
              {(["rendu", "source", "edition"] as const).map((cle) => (
                <button
                  key={cle}
                  type="button"
                  role="tab"
                  aria-selected={vue === cle}
                  onClick={() => setVue(cle)}
                  className={`rounded px-1.5 py-0.5 text-micro capitalize transition-colors ${
                    vue === cle
                      ? "bg-violet-500/15 text-violet-200"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {cle === "edition" ? "Modifier" : cle}
                </button>
              ))}
            </div>
            <span
            className={`rounded px-1.5 py-0.5 text-micro ${
              detail.is_builtin
                ? "bg-zinc-800 text-zinc-400"
                : "bg-violet-500/15 text-violet-200"
            }`}
          >
            {detail.is_builtin ? "natif" : "personnalisé"}
            </span>
          </div>
        )}
      </div>

      {erreur && (
        <p className="px-4 py-3 text-xs text-red-400">
          Impossible de lire la définition de cet agent : {erreur}
        </p>
      )}

      {detail && (
        <>
          <p className="border-b border-zinc-800 px-4 py-2 text-micro text-zinc-500">
            Ce texte est envoyé en tête de chaque appel de cet agent. Il décide
            de tout ce qu'il fait.
          </p>
          {vue === "rendu" && (
            <div className="min-h-0 flex-1 overflow-auto">
              <MarkdownView source={detail.system_prompt} />
            </div>
          )}
          {vue === "source" && (
            <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words px-4 py-3 font-mono text-micro leading-relaxed text-zinc-300">
              {detail.system_prompt}
            </pre>
          )}
          {vue === "edition" && (
            <div className="flex min-h-0 flex-1 flex-col gap-2 p-4">
              <textarea
                value={brouillon}
                onChange={(e) => setBrouillon(e.target.value)}
                spellCheck={false}
                className="min-h-0 flex-1 resize-none rounded border border-zinc-700 bg-zinc-950 p-3 font-mono text-micro leading-relaxed text-zinc-200 outline-none focus:border-zinc-500"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void enregistrer()}
                  disabled={enregistrement}
                  className="rounded border border-violet-500/50 bg-violet-500/15 px-2 py-1 text-mini text-violet-200 transition-colors hover:border-violet-400 disabled:opacity-50"
                >
                  {enregistrement ? "Enregistrement…" : "Enregistrer"}
                </button>
                {message && (
                  <span className="text-mini text-zinc-400">{message}</span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
