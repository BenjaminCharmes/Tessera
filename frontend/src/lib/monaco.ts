import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/language/json/json.worker?worker";
import tsWorker from "monaco-editor/language/typescript/ts.worker?worker";

let configured = false;

/**
 * Configure the Monaco environment to use local bundled workers.
 * Safe to call multiple times — only the first call takes effect.
 *
 * ADR-012 : Monaco bundlé via Vite, sans CDN — seul le moment du chargement
 * change. Appelé depuis Editor/index.tsx, lui-même chargé en lazy depuis
 * CenterView (ticket-355). La configuration s'exécute donc uniquement
 * à la première ouverture de l'éditeur, pas au démarrage de l'application.
 */
export function configureMonaco(): void {
  if (configured) return;
  configured = true;

  window.MonacoEnvironment = {
    getWorker(_: string, label: string): Worker {
      if (label === "json") return new jsonWorker();
      if (label === "typescript" || label === "javascript") return new tsWorker();
      return new editorWorker();
    },
  };

  loader.config({ monaco });
}
