import AgentBadge from "../../design/AgentBadge";
import InfoTip from "../../design/InfoTip";
import { useMemo, useState } from "react";
import MarkdownView from "../Editor/MarkdownView";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import { useAgents } from "../../hooks/useAgents";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import type { AgentDetail as AgentDetailData } from "../../types/api";
import { diffLignes } from "./diff";
import { phraseDuRole } from "./chiffres";
import PromptDiff from "./PromptDiff";

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
 *
 * Le modèle et les chiffres du rôle vivent dans la colonne de droite de la
 * fiche (ticket-429) ; ici reste ce que l'agent *dit* : phrase et prompt.
 */
export default function Definition({ role }: { role: string }) {
  const fetcher = useMemo(() => () => api.agents.detail(role), [role]);
  const charge = useResource<AgentDetailData | null>(fetcher, null);
  const { agents } = useAgents();
  /** Ce que le dernier enregistrement a rendu, prioritaire sur la lecture. */
  const [enregistre, setEnregistre] = useState<AgentDetailData | null>(null);
  const detail = enregistre ?? charge.data;
  const erreur = charge.error;

  const [vue, setVue] = useState<"rendu" | "source" | "edition">("rendu");
  const [brouillonEdite, setBrouillon] = useState<string | null>(null);
  const brouillon = brouillonEdite ?? detail?.system_prompt ?? "";
  const [enregistrement, setEnregistrement] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  /** Vrai quand le diff de confirmation est affiché (ticket-226). */
  const [diffOuvert, setDiffOuvert] = useState(false);

  const lignesDiff = useMemo(
    () => (diffOuvert ? diffLignes(detail?.system_prompt ?? "", brouillon) : []),
    [diffOuvert, detail?.system_prompt, brouillon],
  );

  /** Vérifie les préconditions et ouvre le diff de confirmation. */
  function demanderConfirmation() {
    if (!brouillon.trim()) {
      setMessage("Un prompt vide priverait l'agent de toute définition.");
      return;
    }
    if (brouillon === (detail?.system_prompt ?? "")) {
      return;
    }
    setDiffOuvert(true);
  }

  async function confirmer() {
    setEnregistrement(true);
    setMessage(null);
    try {
      setEnregistre(await api.agents.updatePrompt(role, brouillon));
      setDiffOuvert(false);
      setMessage("Enregistré. Il s'applique au prochain appel de cet agent.");
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setEnregistrement(false);
    }
  }

  const phrase = detail
    ? phraseDuRole(
        agents.find((a) => a.role === role)?.description,
        detail.system_prompt,
      )
    : "";

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>{role}</RegionTitle>
        {detail && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-0.5" role="tablist" aria-label="Affichage du prompt">
              {(["rendu", "source", "edition"] as const).map((cle) => (
                <button
                  key={cle}
                  type="button"
                  role="tab"
                  aria-selected={vue === cle}
                  onClick={() => setVue(cle)}
                  className={`rounded px-1.5 py-0.5 text-micro capitalize transition-colors ${
                    vue === cle
                      ? "bg-violet-500/15 text-zinc-100"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {cle === "edition" ? "Modifier" : cle}
                </button>
              ))}
            </div>
            <AgentBadge moment={detail.moment ?? "jamais"} />
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
          {phrase && (
            <p className="border-b border-zinc-800 px-4 py-2 text-xs text-zinc-300">
              {phrase}
            </p>
          )}
          <div className="flex items-center gap-1 border-b border-zinc-800 px-4 py-2">
            <span className="text-micro text-zinc-500">Prompt système</span>
            <InfoTip>
              {"Ce texte est envoyé en tête de chaque appel de cet agent. Il décide de tout ce qu'il fait."}
            </InfoTip>
          </div>
          {vue === "rendu" && (
            <div className="min-h-0 flex-1 overflow-auto">
              <MarkdownView source={detail.system_prompt} />
            </div>
          )}
          {vue === "source" && (
            <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap wrap-break-word px-4 py-3 font-mono text-micro leading-relaxed text-zinc-300">
              {detail.system_prompt}
            </pre>
          )}
          {vue === "edition" && (
            <div className="flex min-h-0 flex-1 flex-col gap-2 p-4">
              {!diffOuvert ? (
                <>
                  <textarea
                    value={brouillon}
                    onChange={(e) => setBrouillon(e.target.value)}
                    spellCheck={false}
                    className="min-h-0 flex-1 resize-none rounded-sm border border-zinc-700 bg-zinc-950 p-3 font-mono text-micro leading-relaxed text-zinc-200 outline-hidden focus:border-zinc-500"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={demanderConfirmation}
                      className="rounded-sm border border-violet-500/50 bg-violet-500/15 px-2 py-1 text-mini text-zinc-100 transition-colors hover:border-violet-400"
                    >
                      Enregistrer
                    </button>
                    {message && (
                      <span className="text-mini text-zinc-400">{message}</span>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <PromptDiff lignes={lignesDiff} />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void confirmer()}
                      disabled={enregistrement}
                      className="rounded-sm border border-violet-500/50 bg-violet-500/15 px-2 py-1 text-mini text-zinc-100 transition-colors hover:border-violet-400 disabled:opacity-50"
                    >
                      {enregistrement ? "Enregistrement…" : "Confirmer"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setDiffOuvert(false)}
                      className="rounded-sm border border-zinc-600 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-400"
                    >
                      Annuler
                    </button>
                    {message && (
                      <span className="text-mini text-zinc-400">{message}</span>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
