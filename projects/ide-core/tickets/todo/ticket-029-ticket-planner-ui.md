---
id: ticket-029
title: "UI 'Planifier une évolution' + persistance batch"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-028
estimated_days: 2
created: 2026-06-21
---

# ticket-029 — UI Planifier une évolution

## Objectif

Exposer le planificateur (ticket-028) dans l'UI avec une interface en 2 étapes : l'utilisateur décrit son évolution, valide (ou désélectionne) les tickets générés, et les crée en un clic. Le ticket board se rafraîchit automatiquement après création.

## Contexte

Ticket-028 produit des drafts en JSON mais ne les persiste pas. Ce ticket gère la partie frontend (modale 2 étapes) et l'endpoint backend de création batch avec résolution des dépendances locales (`depends_on_index` → vrais ticket IDs).

## Solution proposée

### `frontend/src/components/Sidebar/PlanEvolutionModal.tsx`

**Étape 1 — Description**
```
Décris l'évolution à planifier :
[Je veux ajouter l'authentification OAuth Google          ]
[                                                          ]
                                          [Planifier →]
```

**Étape 2 — Validation des drafts**
```
4 tickets générés — "Auth OAuth Google en 4 tickets"

☑ [high] feat  Configurer OAuth Google (backend)
         Contexte : Intégration Google OAuth2 via httpx-oauth
         Critères : Token validé, Session créée

☑ [high] feat  Page de login OAuth (frontend)
         Dépend de : ticket précédent

☑ [med]  feat  Middleware d'authentification

☐ [low]  chore Tests E2E auth flow

           [← Retour]  [Créer 3 tickets sélectionnés]
```

Checkboxes pour sélectionner/désélectionner. Dépendances résolues vers vrais IDs après création.

### Endpoint batch (backend, dans ce ticket)

`POST /api/v1/projects/{project_id}/tickets/batch`

```json
// Request
{
  "tickets": [
    {
      "title": "...", "type": "feat", "priority": "high",
      "agent": "codeur", "description": "...",
      "acceptance_criteria": ["..."],
      "depends_on_index": []
    }
  ]
}

// Response
{ "created": [{ "id": "ticket-042", ... }, ...] }
```

La résolution `depends_on_index` → vrai `ticket_id` se fait dans `TicketService` : attribuer les IDs séquentiellement, puis substituer.

### Bouton dans `TicketList`

Bouton "⚡ Planifier" dans le header du panneau tickets, à côté de "+ Créer", visible seulement si un projet est sélectionné.

### Types et API client

```typescript
export interface TicketDraft {
  title: string;
  type: string;
  priority: string;
  agent: string;
  description: string;
  acceptance_criteria: string[];
  depends_on_index: number[];
}

export interface PlanResult {
  drafts: TicketDraft[];
  summary: string;
}
```

## Critères d'acceptation

- [ ] L'utilisateur peut décrire une évolution et voir des tickets générés en < 15s
- [ ] Il peut désélectionner certains tickets avant de les créer
- [ ] Les dépendances entre tickets créés sont correctement résolues vers les vrais IDs
- [ ] Le ticket board se rafraîchit automatiquement après création batch
- [ ] Un toast indique le nombre de tickets créés : "3 tickets créés"

## Spécifications techniques

État de la modale : `"idle" | "planning" | "review" | "creating" | "error"`

Résolution des dépendances : si l'utilisateur désélectionne un ticket dont d'autres dépendent, les tickets dépendants voient leur `depends_on_index` filtré (pas de dépendance vers un ticket non créé).

## Dépendances

- **ticket-028** — `POST /projects/{id}/plan` pour générer les drafts.

## Estimation

**2j** — UI 2 étapes + endpoint batch + résolution dépendances + tests RTL et pytest.

## Risques

- **Moyen** — Résolution des dépendances `depends_on_index` → vrais IDs peut être complexe si l'utilisateur désélectionne des tickets intermédiaires. Traiter ce cas edge.
