import MonacoEditor from "@monaco-editor/react";
import { detectLanguage } from "./useMonaco";
import type { Ticket } from "../../types/api";

interface EditorProps {
  ticket: Ticket | null;
}

const WELCOME =
  "# vibe-ide\n\nSelect a project then a ticket from the sidebar.\n";

export default function Editor({ ticket }: EditorProps) {
  return (
    <MonacoEditor
      height="100%"
      theme="vs-dark"
      language={detectLanguage(ticket?.file_path ?? null)}
      value={ticket?.body ?? WELCOME}
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
  );
}
