---
id: ticket-011
title: "Monaco → fichiers réels (lecture/écriture via fs.ts)"
type: feat
status: todo
priority: high
agent: codeur
depends_on:
  - ticket-010
created: 2026-06-20
---

# ticket-011 — Monaco branché sur le filesystem

## Contexte

Monaco Editor est intégré dans l'UI (ticket-007) mais affiche du contenu
statique. `src/lib/fs.ts` expose `readFile/writeFile` mais rien ne l'utilise.
De plus, Monaco chargé depuis le CDN jsdelivr ne fonctionnera pas dans un build
Tauri packagé (pas d'accès internet).

## Tâches

### 1. Bundler Monaco localement (plus CDN)

```bash
cd frontend
npm install monaco-editor
```

Configurer Vite pour les workers Monaco dans `vite.config.ts` :

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ['monaco-editor/esm/vs/language/json/json.worker'],
  },
  worker: { format: 'es' },
})
```

Configurer `MonacoEnvironment` dans `src/main.tsx` :

```typescript
import * as monaco from 'monaco-editor'

window.MonacoEnvironment = {
  getWorker(_: string, label: string) {
    if (label === 'json') {
      return new Worker(
        new URL('monaco-editor/esm/vs/language/json/json.worker', import.meta.url),
        { type: 'module' }
      )
    }
    return new Worker(
      new URL('monaco-editor/esm/vs/editor/editor.worker', import.meta.url),
      { type: 'module' }
    )
  }
}
```

### 2. Mettre à jour `Editor/index.tsx`

```typescript
interface EditorProps {
  ticket: Ticket | null
}

export default function Editor({ ticket }: EditorProps) {
  const [content, setContent] = useState<string>('')
  const [filePath, setFilePath] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Charger le fichier quand le ticket change
  useEffect(() => {
    if (!ticket) { setContent(''); setFilePath(null); return }
    setLoading(true)
    setError(null)
    readFile(ticket.file_path)
      .then(text => { setContent(text); setFilePath(ticket.file_path) })
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false))
  }, [ticket?.file_path])

  // Auto-save avec debounce 500ms
  function handleChange(value: string | undefined) {
    if (!filePath || value === undefined) return
    setContent(value)
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      writeFile(filePath, value).catch(console.error)
    }, 500)
  }
```

Header au-dessus de l'éditeur avec le chemin du fichier actif.

### 3. Scope filesystem Tauri

Dans `src-tauri/tauri.conf.json`, ajouter le scope pour $HOME :

```json
"app": {
  "security": {
    "capabilities": ["default"],
    "assetProtocol": { "enable": true, "scope": ["$HOME/**"] }
  }
}
```

Mettre à jour `capabilities/default.json` pour ajouter les scopes :

```json
"fs:scope-home-recursive"
```

### 4. Gestion des erreurs

- Fichier introuvable → message "Fichier non trouvé : {path}" en overlay
- Erreur d'écriture → notification toast (simple `console.error` pour la v0)
- État de chargement → spinner minimal dans l'éditeur

## Critères d'acceptation

- [ ] Monaco charge sans CDN (bundlé localement)
- [ ] Cliquer sur un ticket charge son fichier `.md` dans Monaco
- [ ] Modifier le contenu dans Monaco auto-sauvegarde le fichier (debounce 500ms)
- [ ] Le chemin du fichier s'affiche dans un header au-dessus de Monaco
- [ ] `npm run build` passe sans erreur (Monaco bundlé dans le dist)
- [ ] `cargo check` passe avec la nouvelle config de scope

## Notes

- `ticket.file_path` est le chemin absolu du fichier ticket Markdown
- Le mode web (sans Tauri) utilise le fallback REST `/api/v1/fs/*` de `fs.ts`
  → ce endpoint n'existe pas encore en backend, ce n'est pas bloquant pour ce ticket
- Ne pas activer TypeScript support Monaco pour la v0 (complexité workers)
