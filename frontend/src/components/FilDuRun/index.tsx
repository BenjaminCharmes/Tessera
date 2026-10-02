import { useState } from "react";
import {
  IconCheck,
  IconCross,
  IconChevronDown,
  IconChevronRight,
} from "../../design/icons";
import TokenStream from "../AgentPanel/TokenStream";
import VerdictBanner from "../AgentPanel/VerdictBanner";
import { verdictDuReviewer } from "./verdict";
import type {
  EntreeFil,
  PassageAgent,
  EntreeSecurite,
  EntreeValidateur,
  EntreeTesteur,
} from "../../hooks/streamState";

// ---------------------------------------------------------------------------
// EnteteVerdict — en-tête commun à toutes les cartes du fil du run
// ---------------------------------------------------------------------------

/** Formate une durée en millisecondes : "2 min 50 s" ou "45 s". */
function formatDuree(ms: number): string {
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return m > 0 ? `${m} min ${rem} s` : `${s} s`;
}

interface EnteteVerdictProps {
  label: string;
  approved: boolean;
  verdictText: string;
  loading?: boolean;
  peutBasculer: boolean;
  ouvert: boolean;
  onToggle?: () => void;
}

/**
 * En-tête partagé par les quatre types de cartes dans le fil du run.
 *
 * Affiche : nom de l'agent | icône + verdict + chevron (si repliable)
 * ou points animés (si le traitement est en cours).
 */
function EnteteVerdict({
  label,
  approved,
  verdictText,
  loading = false,
  peutBasculer,
  ouvert,
  onToggle,
}: EnteteVerdictProps) {
  return (
    <button
      type="button"
      disabled={!peutBasculer}
      onClick={() => peutBasculer && onToggle?.()}
      aria-expanded={ouvert}
      className="flex w-full items-center gap-2 px-3 py-2 bg-zinc-800 text-xs font-semibold text-zinc-300 text-left disabled:cursor-default"
    >
      <span>{label}</span>

      {loading ? (
        <span className="ml-auto flex gap-0.5">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </span>
      ) : (
        <span
          className={`ml-auto flex items-center gap-1 font-normal ${
            approved ? "text-green-400" : "text-red-400"
          }`}
        >
          {approved ? <IconCheck size={12} /> : <IconCross size={12} />}
          <span>{verdictText}</span>
          {peutBasculer &&
            (ouvert ? (
              <IconChevronDown size={12} />
            ) : (
              <IconChevronRight size={12} />
            ))}
        </span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// EntreePipeline — passage d'un agent (codeur ou reviewer)
// ---------------------------------------------------------------------------

interface EntreePipelineProps {
  entry: PassageAgent;
  isLast: boolean;
}

/**
 * Un passage d'agent dans le fil — repliable quand terminé et pas le dernier.
 */
function EntreePipeline({ entry, isLast }: EntreePipelineProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = entry.isDone && !isLast;
  const loading = isLast && !entry.isDone;

  const approved =
    entry.agent === "reviewer"
      ? verdictDuReviewer(entry.content) === "APPROVED"
      : true;

  let verdictText: string;
  if (entry.agent === "reviewer") {
    verdictText = approved ? "APPROVED" : "CHANGES_REQUESTED";
  } else if (peutBasculer && entry.duration_ms !== undefined) {
    verdictText = `terminé · ${formatDuree(entry.duration_ms)}`;
  } else {
    verdictText = "terminé";
  }

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label={entry.agent.toUpperCase()}
        approved={approved}
        verdictText={verdictText}
        loading={loading}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          {entry.agent === "codeur" && !entry.isDone && entry.tokens && (
            <TokenStream tokens={entry.tokens} isActive={isLast} />
          )}
          {entry.agent === "codeur" && entry.isDone && entry.content && (
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap wrap-break-word rounded-sm bg-zinc-950/60 p-2 font-mono text-mini text-zinc-300">
              {entry.content}
            </pre>
          )}
          {entry.agent === "reviewer" && entry.content && (
            <VerdictBanner content={entry.content} />
          )}
          {!entry.tokens && !entry.content && (
            <div className="text-zinc-600 text-xs italic">Génération…</div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EntreeSecuriteView — résultat de l'audit de sécurité
// ---------------------------------------------------------------------------

interface EntreeSecuriteViewProps {
  entry: EntreeSecurite;
  isLast: boolean;
}

function EntreeSecuriteView({ entry, isLast }: EntreeSecuriteViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const approved = entry.verdict !== "BLOCK";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="SÉCURITÉ"
        approved={approved}
        verdictText={entry.verdict}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && entry.summary && (
        <div className="p-3 text-xs text-zinc-400">{entry.summary}</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EntreeValidateurView — résultat de la validation, critère par critère
// ---------------------------------------------------------------------------

interface EntreeValidateurViewProps {
  entry: EntreeValidateur;
  isLast: boolean;
}

function EntreeValidateurView({ entry, isLast }: EntreeValidateurViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const approved = entry.verdict === "APPROVED";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="VALIDATEUR"
        approved={approved}
        verdictText={entry.verdict}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          {entry.feedback && (
            <p className="mb-2 text-xs text-zinc-400">{entry.feedback}</p>
          )}
          <ul className="space-y-1.5">
            {entry.criteria.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span
                  className={`shrink-0 mt-0.5 ${c.passed ? "text-green-400" : "text-red-400"}`}
                >
                  {c.passed ? <IconCheck size={12} /> : <IconCross size={12} />}
                </span>
                <span>
                  <span
                    className={`font-medium ${c.passed ? "text-green-400" : "text-red-400"}`}
                  >
                    {c.criterion}
                  </span>
                  {c.note && (
                    <span className="ml-1 text-zinc-400">{c.note}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EntreeTesteurView — résultat de la suite de tests (ticket-321)
// ---------------------------------------------------------------------------

interface EntreeTesteurViewProps {
  entry: EntreeTesteur;
  isLast: boolean;
}

/**
 * Une entrée du testeur dans le fil — repliable quand terminée et non-dernière.
 *
 * En rouge, elle dit que le run repart au codeur sans passer par la revue.
 */
function EntreeTesteurView({ entry, isLast }: EntreeTesteurViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const verdictText = entry.passed
    ? "tests ok"
    : "retour au codeur, sans revue";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="TESTEUR"
        approved={entry.passed}
        verdictText={verdictText}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          <p className="mb-2 text-xs text-zinc-400">{entry.output_summary}</p>
          {!entry.passed && entry.errors.length > 0 && (
            <ul className="space-y-1">
              {entry.errors.map((err, i) => (
                <li key={i} className="font-mono text-xs text-red-400">
                  {err}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FilDuRun — export principal
// ---------------------------------------------------------------------------

interface FilDuRunProps {
  entries: EntreeFil[];
}

/**
 * Fil chronologique d'un run : agents, sécurité et validateur dans l'ordre.
 *
 * Partagé entre RunView (vue centrée du run) et AgentPanel (panneau latéral).
 * Les entrées terminées et non-dernières sont repliées ; la dernière reste
 * dépliée. Un observateur arrivé après le début n'a aucune entrée : le
 * composant parent gère ce repli avec `blocsDuPanneau` (ticket-257).
 */
export default function FilDuRun({ entries }: FilDuRunProps) {
  return (
    <>
      {entries.map((entry, idx) => {
        const isLast = idx === entries.length - 1;
        if (entry.genre === "securite") {
          return (
            <EntreeSecuriteView key={entry.id} entry={entry} isLast={isLast} />
          );
        }
        if (entry.genre === "validateur") {
          return (
            <EntreeValidateurView
              key={entry.id}
              entry={entry}
              isLast={isLast}
            />
          );
        }
        if (entry.genre === "testeur") {
          return (
            <EntreeTesteurView key={entry.id} entry={entry} isLast={isLast} />
          );
        }
        return <EntreePipeline key={entry.id} entry={entry} isLast={isLast} />;
      })}
    </>
  );
}
