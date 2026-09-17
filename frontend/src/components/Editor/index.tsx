import { BAND } from "../../design/layout";
import { useEffect, useState } from "react";
import MonacoEditor from "@monaco-editor/react";
import { detectLanguage } from "./useMonaco";
import { readFile } from "../../lib/fs";
import type { Ticket } from "../../types/api";

interface EditorProps {
  ticket: Ticket | null;
  /** Fichier ouvert depuis l'arbre ; prioritaire sur celui du ticket. */
  openFilePath?: string | null;
}

/**
 * Lecteur de fichier (ticket-065).
 *
 * L'éditeur est **en lecture seule** depuis le pivot cockpit : vibe-ide
 * orchestre, VSCode édite. Monaco reste parce qu'il coloriera un diff mieux
 * qu'un `<pre>`, pas parce qu'on prétend remplacer un éditeur — il n'y a ici
 * ni LSP, ni recherche multi-fichiers, ni debugger, et il n'y en aura pas.
 *
 * L'écriture passait par un `PUT /fs/write` débouncé : un fichier modifié ici
 * pendant qu'un agent travaille sur la même branche produisait un conflit que
 * personne n'arbitrait. Le bouton « Ouvrir dans VSCode » de l'en-tête de projet
 * remplace ce chemin.
 */

const WELCOME =
  "# vibe-ide\n\nSélectionne un projet puis un ticket dans la sidebar.\n";

export default function Editor({ ticket, openFilePath = null }: EditorProps) {
  const [content, setContent] = useState<string>(WELCOME);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cible = openFilePath ?? ticket?.file_path ?? null;
    if (!cible) {
      setContent(WELCOME);
      setFilePath(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    readFile(cible)
      .then((text) => {
        setContent(text);
        setFilePath(cible);
      })
      .catch((err: unknown) => {
        setError(`Impossible de lire le fichier : ${String(err)}`);
        setContent("");
        setFilePath(null);
      })
      .finally(() => setLoading(false));
  }, [openFilePath, ticket?.file_path]);

  const language = detectLanguage(filePath ?? openFilePath ?? ticket?.file_path ?? null);

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
      </div>

      {/* Erreur */}
      {error && (
        <div className="border-b border-red-800 bg-red-950 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Éditeur Monaco */}
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
    </div>
  );
}
