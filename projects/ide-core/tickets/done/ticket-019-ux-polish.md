---
id: ticket-019
title: "UX polish — ErrorBoundary, empty states, toasts"
type: chore
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-017
  - ticket-018
created: 2026-06-20
---

# ticket-019 — UX polish

## Contexte

L'IDE est fonctionnel mais manque de plusieurs éléments de qualité UX :
- Les erreurs React non attrapées crashent l'UI entière sans message
- Les états vides (aucun projet, aucun ticket) affichent des divs generiques
- Les actions réussies (création projet/ticket, pipeline terminé) n'ont pas de feedback
- Pas de skeleton loading — l'UI est vide puis s'affiche d'un coup

## Tâches

### 1. `src/components/ErrorBoundary.tsx`

```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, { error: Error | null }> {
  // getDerivedStateFromError + componentDidCatch
  // Affiche fallback ou un panneau d'erreur générique cohérent avec le thème
}
```

Wrapper autour de :
- `<Sidebar>` (crash ne casse pas l'éditeur)
- `<Editor>` (crash ne casse pas la sidebar)
- `<AgentPanel>` (crash ne casse pas le reste)

### 2. Empty states cohérents

| Situation | Actuel | Cible |
|-----------|--------|-------|
| Aucun projet dans la workspace | "No projects found" | Panel avec message + bouton "+ Créer un projet" |
| Projet sélectionné mais aucun ticket | `TicketList` vide | "Aucun ticket pour l'instant — créez-en un avec +" |
| Aucun pipeline dans l'historique | Liste vide | "Aucun pipeline lancé sur ce projet" |
| Éditeur sans ticket sélectionné | Welcome text | Garder le welcome text, améliorer le style |

### 3. `src/components/Toast.tsx` + `src/hooks/useToast.ts`

Toast léger (pas de librairie externe) :
```typescript
interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
  duration?: number  // ms, défaut 3000
}

export function useToast(): {
  toasts: Toast[]
  addToast: (message: string, type: Toast['type']) => void
  removeToast: (id: string) => void
}
```

Affichage : coins bas-droit, empilables, auto-dismiss.

Déclencher un toast pour :
- Création projet réussie → "Projet créé ✓"
- Création ticket réussie → "Ticket créé ✓"
- `pipeline_done` approved → "ticket-XXX approuvé ✓"
- `pipeline_done` blocked → "ticket-XXX bloqué après 3 tours"
- Erreur API → message d'erreur

### 4. Skeleton loading

Pour `ProjectNav` et `TicketList` : remplacer le texte "Loading…"
par des rectangles animés (`animate-pulse bg-zinc-800`).

```tsx
function SkeletonItem() {
  return <div className="h-8 mx-3 my-1 rounded bg-zinc-800 animate-pulse" />
}
```

### 5. Tests

- `ErrorBoundary.test.tsx` : composant crashant → fallback rendu
- `useToast.test.ts` : addToast, removeToast, auto-dismiss après duration
- `Toast.test.tsx` : rendu, types (success/error/info), dismiss

## Critères d'acceptation

- [ ] ErrorBoundary sur Sidebar, Editor, AgentPanel — crash isolé, pas de white screen
- [ ] Empty state "Créer un projet" avec CTA dans ProjectNav
- [ ] Empty state "Créer un ticket" avec CTA dans TicketList
- [ ] Toast success à chaque création (projet, ticket)
- [ ] Toast pipeline_done (approved ou blocked)
- [ ] Skeleton loading (3 items) pendant le chargement de la liste projets et tickets
- [ ] `npm run test` vert
