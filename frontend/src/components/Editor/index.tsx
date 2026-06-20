import { useEffect, useRef, useState } from "react";
import MonacoEditor from "@monaco-editor/react";
import { detectLanguage } from "./useMonaco";
import { readFile, writeFile } from "../../lib/fs";
import type { Ticket } from "../../types/api";

interface EditorProps {
  ticket: Ticket | null;
}

const WELCOME =
  "# vibe-ide\n\nSélectionne un projet puis un ticket dans la sidebar.\n";
const DEBOUNCE_MS = 500;

export default function Editor({ ticket }: EditorProps) {
  const [content, setContent] = useState<string>(WELCOME);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!ticket) {
      setContent(WELCOME);
      setFilePath(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    readFile(ticket.file_path)
      .then((text) => {
        setContent(text);
        setFilePath(ticket.file_path);
      })
      .catch((err: unknown) => {
        setError(`Impossible de lire le fichier : ${String(err)}`);
        setContent("");
        setFilePath(null);
      })
      .finally(() => setLoading(false));
  }, [ticket?.file_path]);

  function handleChange(value: string | undefined) {
    if (value === undefined || !filePath) return;
    setContent(value);

    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      writeFile(filePath, value).catch((err: unknown) => {
        console.error("Erreur sauvegarde:", err);
      });
    }, DEBOUNCE_MS);
  }

  const language = detectLanguage(filePath ?? ticket?.file_path ?? null);

  return (
    <div className="flex h-full flex-col">
      {/* Header : chemin du fichier actif */}
      <div className="flex items-center gap-2 border-b border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-400">
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
          onChange={handleChange}
          options={{
            minimap: { enabled: false },
            wordWrap: "on",
            fontSize: 14,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            readOnly: loading,
            padding: { top: 16 },
          }}
        />
      </div>
    </div>
  );
}
