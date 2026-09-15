---
id: ticket-018
title: "UI — Panneau historique des pipelines"
type: feat
status: done
priority: medium
agent: codeur
depends_on:
  - ticket-015
  - ticket-017
created: 2026-06-20
---

# ticket-018 — Historique des pipelines (UI)

## Contexte

Le backend expose `GET /api/v1/projects/{id}/runs` depuis ticket-015.
Ce ticket ajoute un troisième panel dans la sidebar ("Historique") qui affiche
les derniers pipelines du projet actif avec leur statut et durée.

## Tâches

### 1. `src/lib/api.ts` — endpoint runs

```typescript
runs: {
  list: (projectId: string, limit = 20): Promise<PipelineRun[]> =>
    get(`/projects/${projectId}/runs?limit=${limit}`),
}
```

```typescript
// src/types/api.ts
export interface PipelineRun {
  id: string
  ticket_id: string
  started_at: string       // ISO 8601
  finished_at: string | null
  rounds: number | null
  approved: boolean | null
  final_status: string | null
}
```

### 2. `src/hooks/useRuns.ts`

```typescript
export function useRuns(projectId: string | null): UseRunsResult {
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Refresh déclenchable depuis l'extérieur (appelé à pipeline_done)
  const refresh = useCallback(() => { ... }, [projectId])

  useEffect(() => { refresh() }, [projectId])

  return { runs, loading, error, refresh }
}
```

### 3. `src/components/Sidebar/RunHistory.tsx`

Affiche la liste des runs :

```
▣ ticket-011  ✅ done    2 tours  1m 23s   20/06 14:32
▣ ticket-009  ⛔ blocked 3 tours  4m 01s   20/06 13:58
▣ ticket-008  ✅ done    1 tour   0m 47s   20/06 12:41
```

Détails d'un run (expansion on click) :
- started_at / finished_at (heure locale)
- rounds, approved, final_status
- Lien vers le ticket dans la sidebar (click → sélectionne le ticket)

### 4. Intégration dans `Sidebar/index.tsx` et `IconBar`

Ajouter un troisième bouton dans l'IconBar : `⏱` (ou `▶`) → panel "history"

```typescript
type SidebarPanel = "projects" | "tickets" | "history"
```

### 5. Refresh auto à `pipeline_done`

Dans `App.tsx`, quand un event `pipeline_done` est reçu → appeler `runsRefresh()`.

### 6. Tests

- `useRuns.test.ts` :
  - Charge la liste au montage
  - `refresh()` retrigger le fetch
  - Gestion d'erreur API
- `RunHistory.test.tsx` :
  - Rendu liste avec durée calculée
  - État loading et erreur
  - Expansion d'un run (détails)

## Critères d'acceptation

- [ ] Troisième panel "Historique" dans la sidebar avec son icône
- [ ] Liste les N derniers runs avec ticket_id, statut, rounds, durée
- [ ] Durée = `finished_at - started_at` formatée en "Xm Ys"
- [ ] Refresh automatique quand `pipeline_done` reçu (ticket-017)
- [ ] Clic sur un run → sélectionne le ticket correspondant dans la sidebar
- [ ] `npm run test` vert

## Notes

- Durée affichée uniquement si `finished_at` est non-null (run en cours → "En cours…")
- Ne pas afficher les events individuels dans ce panel (trop verbeux) — juste le résumé
- Tri par `started_at DESC` (déjà fait par le backend)
