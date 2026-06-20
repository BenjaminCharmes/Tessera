---
id: ticket-017
title: "Live ticket board — mise à jour temps réel via WebSocket"
type: feat
status: todo
priority: high
agent: codeur
depends_on:
  - ticket-009
created: 2026-06-20
---

# ticket-017 — Live ticket board

## Contexte

Actuellement, le ticket board (kanban) affiche un snapshot figé au chargement.
Quand un pipeline tourne, le ticket passe par `in-progress → in-review → done`,
mais l'UI ne reflète ces changements qu'après un refresh manuel.

Les events WebSocket `ticket_status_changed` et `pipeline_done` sont déjà émis
par l'Orchestrateur (ticket-009). Ce ticket branche le board dessus.

## Tâches

### 1. `src/hooks/useTickets.ts` (nouveau hook ou modification de useProjects pattern)

```typescript
export function useTickets(projectId: string | null): UseTicketsResult {
  const [byStatus, setByStatus] = useState<Record<TicketStatus, Ticket[]>>({...})
  const [loading, setLoading] = useState(false)
  const { events } = useOrchestratorStream(projectId)

  // Charge la liste initiale via API
  useEffect(() => { /* fetch */ }, [projectId])

  // Applique les mises à jour temps réel
  useEffect(() => {
    const last = events[events.length - 1]
    if (!last) return
    if (last.type === 'ticket_status_changed') {
      // Déplace le ticket dans le bon bucket sans re-fetch
      setByStatus(prev => moveTicket(prev, last.ticket_id, last.data.status))
    }
  }, [events])

  return { byStatus, loading, refresh }
}
```

### 2. Fonction pure `moveTicket`

```typescript
function moveTicket(
  byStatus: Record<TicketStatus, Ticket[]>,
  ticketId: string,
  newStatus: TicketStatus,
): Record<TicketStatus, Ticket[]> {
  // Cherche le ticket dans tous les buckets, le retire, l'ajoute dans newStatus
  // Retourne un nouvel objet (immutable)
}
```

### 3. Indicateurs visuels dans `TicketCard`

Quand un ticket est `in-progress` ou `in-review` ET qu'un pipeline tourne :
- Badge animé "En cours" sur la carte (déjà `animate-pulse`, améliorer le label)
- Badge round count si `agent_started` reçu pour ce ticket : "Tour 1/3"

### 4. Notification `pipeline_done` dans le header du board

Quand `pipeline_done` arrive :
- Toast ou bannière 3 secondes : "✅ ticket-XXX approuvé" ou "⛔ ticket-XXX bloqué"
- Auto-dismiss après 3s

### 5. Connecter `useOrchestratorStream` dans `App.tsx`

L'app maintient déjà `useOrchestratorStream` pour l'AgentPanel.
Partager le même stream (via state lift ou context) plutôt que d'ouvrir deux WS.

**Option retenue** : passer les `events` de `useOrchestratorStream` (déjà en place
dans App.tsx) directement au hook `useTickets` en prop ou via le state partagé.

### 6. Tests

- `useTickets.test.ts` :
  - Charge la liste initiale
  - `ticket_status_changed` event → ticket déplacé dans le bon bucket
  - `pipeline_done` event → toast déclenché
  - Immutabilité : le bucket précédent n'est pas muté
- `moveTicket.test.ts` : tests unitaires de la fonction pure

## Critères d'acceptation

- [ ] Ticket passe de `todo` → `in-progress` → `in-review` → `done` dans l'UI
  sans aucun refresh manuel pendant un pipeline
- [ ] Un seul WebSocket ouvert par session (pas de doublon)
- [ ] Badge "Tour N/3" visible pendant l'exécution
- [ ] Toast 3s à `pipeline_done`
- [ ] Tests unitaires de `moveTicket` (immutabilité garantie)
- [ ] `npm run test` vert

## Notes

- Ne pas ouvrir un deuxième WS — réutiliser le stream existant de l'AgentPanel
- La reconnexion automatique existe déjà dans `useOrchestratorStream` (3 retries)
- `moveTicket` doit être une fonction pure testée séparément
