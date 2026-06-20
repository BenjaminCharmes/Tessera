---
id: ticket-011
title: "Monaco → fichiers réels (lecture/écriture via fs.ts)"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-010
created: 2026-06-20
completed: 2026-06-20
---

# ticket-011 — Monaco branché sur le filesystem ✅

## Ce qui a été fait

### Monaco bundlé localement

- `monaco-editor` npm installé (v0.55.1)
- Workers configurés via `?worker` Vite (compatible Rolldown/Vite 8)
- `loader.config({ monaco })` configure `@monaco-editor/react` pour utiliser le package local
- Suppression de la référence CDN jsdelivr dans la CSP

**Note Rolldown** : `new URL('monaco-editor/...', import.meta.url)` ne fonctionne pas
avec Rolldown (résout vers `src/` au lieu de `node_modules/`). Solution : `?worker` suffix.

### `src/main.tsx`

```typescript
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";

window.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === "json") return new jsonWorker();
    if (label === "typescript" || label === "javascript") return new tsWorker();
    return new editorWorker();
  },
};

loader.config({ monaco });
```

### `Editor/index.tsx` — lecture/écriture via `fs.ts`

- `useEffect` sur `ticket.file_path` → `readFile()` charge le contenu
- `onChange` → `writeFile()` avec debounce 500ms
- Header avec le chemin du fichier actif
- État de chargement (`readOnly` Monaco pendant le load)
- Overlay d'erreur si fichier introuvable

### Capabilities Tauri

- `fs:scope-home-recursive` ajouté → accès `$HOME/**`
- CSP: suppression CDN jsdelivr (plus nécessaire), ajout `worker-src blob:`

## Validation

- `npm run build` ✅ (bundle 3.9MB / gzip 1MB — normal avec Monaco)
- `cargo check` ✅
- Warning taille de chunk attendu (Monaco est gros par nature)
