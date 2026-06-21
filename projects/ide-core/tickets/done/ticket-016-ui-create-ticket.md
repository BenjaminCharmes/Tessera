---
id: ticket-016
title: "UI — Création de ticket depuis la sidebar"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-014
created: 2026-06-20
---

# ticket-016 — UI création de ticket

## Contexte

Le backend expose `POST /api/v1/projects/{id}/tickets` depuis ticket-001.
Actuellement, les tickets ne peuvent être créés qu'en éditant des fichiers Markdown
à la main. Ce ticket ajoute un bouton "+" dans le panel Tickets de la sidebar
avec un modal de création structuré.

## Tâches

### 1. Endpoint dans `src/lib/api.ts`

```typescript
tickets: {
  list: (projectId: string) => get<Ticket[]>(`/projects/${projectId}/tickets`),
  create: (projectId: string, data: CreateTicketPayload) =>
    post<Ticket>(`/projects/${projectId}/tickets`, data),
}
```

```typescript
interface CreateTicketPayload {
  title: string
  type: TicketType           // 'feat' | 'fix' | 'chore' | 'design' | 'docs'
  priority: TicketPriority   // 'critical' | 'high' | 'medium' | 'low'
  description: string        // corps Markdown du ticket
}
```

### 2. `src/components/Sidebar/CreateTicketModal.tsx`

```typescript
interface CreateTicketModalProps {
  projectId: string
  onClose: () => void
  onCreated: (ticket: Ticket) => void
}
```

Champs du formulaire :
- `title` (requis, max 100 chars)
- `type` : select parmi `feat | fix | chore | design | docs` (défaut: feat)
- `priority` : select parmi `critical | high | medium | low` (défaut: medium)
- `description` : textarea Markdown (optionnel, max 2000 chars)

Comportement :
- Validation inline (title requis)
- État loading pendant le POST
- Affichage erreur API
- Fermeture : Escape, overlay, Annuler

### 3. Bouton "+" dans `TicketList/index.tsx`

Dans le header de la liste de tickets, à côté des filtres de statut :

```tsx
<button
  onClick={() => setShowCreateModal(true)}
  title="Nouveau ticket"
  aria-label="Créer un ticket"
>
  +
</button>
```

Après création :
- Rafraîchir la liste des tickets
- Le nouveau ticket apparaît dans la colonne `todo`

### 4. Backend — vérifier le endpoint `POST /tickets`

S'assurer que `POST /api/v1/projects/{id}/tickets` accepte bien `title`, `type`,
`priority`, `description` et génère le fichier Markdown correspondant dans `todo/`.

### 5. Tests

- `CreateTicketModal.test.tsx` :
  - Rendu formulaire (title, type, priority, description, boutons)
  - Validation : title requis
  - Submit → `api.tickets.create(projectId, payload)` appelé
  - Loading state (bouton Créer désactivé)
  - Erreur API affichée
  - `onCreated(ticket)` appelé après succès
  - `onClose()` sur Annuler / Escape / overlay

## Critères d'acceptation

- [ ] Bouton "+" visible dans le panel Tickets (seulement si un projet est sélectionné)
- [ ] Modal avec titre, type, priorité, description
- [ ] Validation : title requis (message inline)
- [ ] POST `/api/v1/projects/{id}/tickets` appelé
- [ ] Nouveau ticket apparaît en tête de la colonne `todo` sans rechargement de page
- [ ] `npm run test` toujours vert
