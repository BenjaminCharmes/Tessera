import { BAND } from "../../design/layout";
import { useMemo, useState } from "react";
import MarkdownView from "./MarkdownView";
import MonacoEditor from "@monaco-editor/react";
import { detectLanguage } from "./useMonaco";
import { readFile } from "../../lib/fs";
// Configure Monaco workers and loader before first render (ADR-012, ticket-355).
import { configureMonaco } from "../../lib/monaco";
configureMonaco();
import { useResource } from "../../hooks/useResource";
import RunHistorique from "../StatsView/RunHistorique";
import TicketRuns from "./TicketRuns";
import type { Ticket } from "../../types/api";

interface EditorProps {
  ticket: Ticket | null;
  /** Fichier ouvert depuis l'arbre ; prioritaire sur celui du ticket. */
  openFilePath?: string | null;
  /** Projet affiché : sans lui, la lecture ne passe pas par le cache (ticket-356). */
  projectId?: string | null;
}

/**
 * Lecteur de fichier (ticket-065).
 *
 * L'éditeur est **en lecture seule** depuis le pivot cockpit : Tessera
 * orchestre, VSCode édite. Monaco reste parce qu'il coloriera un diff mieux
 * qu'un `<pre>`, pas parce qu'on prétend remplacer un éditeur — il n'y a ici
 * ni LSP, ni recherche multi-fichiers, ni debugger, et il n'y en aura pas.
 *
 * L'écriture passait par un `PUT /fs/write` débouncé : un fichier modifié ici
 * pendant qu'un agent travaille sur la même branche produisait un conflit que
 * personne n'arbitrait. Le bouton « Ouvrir dans VSCode » de l'en-tête de projet
 * remplace ce chemin.
 *
 * La lecture passe par `useResource` : deux clics rapides dans l'arbre
 * faisaient arriver la lecture du premier fichier après celle du second, et
 * son contenu s'affichait sous l'en-tête de l'autre (ticket-123).
 */

const WELCOME =
  "# Tessera\n\nSélectionne un projet puis un ticket dans la sidebar.\n";

export default function Editor({
  ticket,
  openFilePath = null,
  projectId = null,
}: EditorProps) {
  const cible = openFilePath ?? ticket?.file_path ?? null;
  const fetcher = useMemo(
    () => (cible ? () => readFile(cible) : null),
    [cible],
  );
  // La clé de cache porte le projet et le chemin du fichier : le contenu d'un
  // projet ne s'affiche jamais sous un autre (ticket-356).
  const lecture = useResource<string | null>(
    fetcher,
    null,
    projectId && cible ? { projet: projectId, ressource: cible } : undefined,
  );

  const filePath = cible;
  const loading = lecture.loading;
  const error = lecture.error
    ? `Impossible de lire le fichier : ${lecture.error}`
    : null;
  const content = cible === null ? WELCOME : (lecture.data ?? "");

  const language = detectLanguage(filePath);
  const estMarkdown = (filePath ?? "").toLowerCase().endsWith(".md");
  // Le rendu est le défaut sur un Markdown : tickets, ADR et notes se lisent
  // comme des documents, pas comme du source (ticket-078).
  const [vueRendue, setVueRendue] = useState(true);

  // Le run rouvert depuis la bande du ticket (ticket-332). Rattaché à son
  // ticket : en sélectionner un autre, ou ouvrir un fichier, le referme.
  const [revu, setRevu] = useState<{ ticketId: string; runId: string } | null>(null);
  const ticketAffiche = openFilePath === null ? ticket : null;

  if (ticketAffiche && revu?.ticketId === ticketAffiche.id) {
    return (
      <RunHistorique
        runId={revu.runId}
        ticketId={ticketAffiche.id}
        onClose={() => setRevu(null)}
        libelleRetour="Retour au ticket"
      />
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header : chemin du fichier actif */}
      <div className={`${BAND} gap-2 border-b border-zinc-700 bg-zinc-800 px-3 text-xs text-zinc-400`}>
        {filePath ? (
          <span className="truncate font-mono">{filePath}</span>
        ) : (
          <span className="italic">Aucun fichier ouvert</span>
        )}
        {loading && <span className="ml-auto text-zinc-500">chargement…</span>}
        {estMarkdown && !loading && (
          <div className="ml-auto flex items-center gap-0.5" role="tablist" aria-label="Affichage du fichier">
            {[
              { cle: true, libelle: "Rendu" },
              { cle: false, libelle: "Source" },
            ].map(({ cle, libelle }) => (
              <button
                key={libelle}
                type="button"
                role="tab"
                aria-selected={vueRendue === cle}
                onClick={() => setVueRendue(cle)}
                className={`rounded px-1.5 py-0.5 text-micro transition-colors ${
                  vueRendue === cle
                    ? "bg-violet-500/15 text-zinc-100"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {libelle}
              </button>
            ))}
          </div>
        )}
      </div>

      {ticketAffiche && (
        <TicketRuns
          projectId={ticketAffiche.project_id}
          ticketId={ticketAffiche.id}
          onRevoir={(runId) => setRevu({ ticketId: ticketAffiche.id, runId })}
        />
      )}

      {/* Erreur */}
      {error && (
        <div className="border-b border-red-800 bg-red-950 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {estMarkdown && vueRendue && !error ? (
        <MarkdownView source={content} />
      ) : (
      <div className="min-h-0 flex-1">
        <MonacoEditor
          height="100%"
          theme="vs-dark"
          language={language}
          value={content}
          options={{
            minimap: { enabled: false },
            wordWrap: "on",
            fontSize: 14,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            readOnly: true,
            padding: { top: 16 },
          }}
        />
      </div>
      )}
    </div>
  );
}
