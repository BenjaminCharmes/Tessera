---
id: ticket-028
title: "Agent planificateur — tickets depuis une description NL (backend)"
type: feat
status: done
pr_number: 40
priority: medium
agent: codeur
depends_on:
  - ticket-021
estimated_days: 1
created: 2026-06-21
---

# ticket-028 — Agent planificateur (backend)

## Objectif

Permettre à l'utilisateur de décrire une évolution en langage naturel ("Je veux ajouter l'authentification Google") et d'obtenir une liste de tickets bien découpés, ordonnés et avec leurs dépendances. Supprimer la friction de la création manuelle ticket par ticket.

## Contexte

Aujourd'hui l'utilisateur crée ses tickets un par un via le modal `CreateTicketModal`. Pour des évolutions complexes (auth, nouvelle feature, refactor), ce processus prend du temps et l'utilisateur doit lui-même décomposer la feature. Ce ticket délègue ce découpage à un agent spécialisé.

Important : les drafts générés ne sont **pas** persistés par ce service. La persistance est déclenchée explicitement par l'utilisateur via ticket-029 (UI de validation).

## Solution proposée

### `agents/prompts/planificateur.md`

```markdown
Tu es un expert en découpage de features en tickets de développement.
Tu reçois une description d'évolution et le CLAUDE.md du projet comme contexte.

Génère une liste de tickets, du plus fondamental au plus visible.
Chaque ticket doit être implémentable indépendamment en < 4 heures.

Réponds uniquement avec ce JSON :
{
  "tickets": [
    {
      "title": "Titre court et actionnable",
      "type": "feat|fix|refactor|chore",
      "priority": "high|medium|low",
      "agent": "codeur|architect",
      "description": "Contexte et objectif (2-3 phrases)",
      "acceptance_criteria": ["critère observable 1", "critère observable 2"],
      "depends_on_index": [0]
    }
  ],
  "summary": "Résumé en 1-2 phrases de l'évolution planifiée"
}
```

### `backend/src/vibe_ide/services/planner.py`

```python
@dataclass
class TicketDraft:
    title: str
    type: str
    priority: str
    agent: str
    description: str
    acceptance_criteria: list[str]
    depends_on_index: list[int]   # indices dans le tableau courant

@dataclass
class PlanResult:
    drafts: list[TicketDraft]
    summary: str

class PlannerService:
    async def plan(
        self,
        project_id: str,
        description: str,
    ) -> PlanResult:
        # 1. Charger CLAUDE.md du projet comme contexte
        # 2. Appeler Claude avec planificateur.md
        # 3. Extraire JSON via utils.json_extract
        # 4. Valider les depends_on_index (no self-ref, no out-of-bounds)
        # 5. Retourner PlanResult (non persisté)
```

### Endpoint

`POST /api/v1/projects/{project_id}/plan`

```json
// Request
{ "description": "Je veux ajouter l'authentification OAuth Google" }

// Response
{
  "drafts": [
    {
      "title": "Configurer OAuth Google (backend)",
      "type": "feat", "priority": "high", "agent": "codeur",
      "description": "...",
      "acceptance_criteria": ["Token Google validé", "Session créée"],
      "depends_on_index": []
    }
  ],
  "summary": "Auth OAuth Google en 4 tickets (backend + frontend)"
}
```

## Critères d'acceptation

- [ ] Une description d'évolution produit entre 2 et 8 tickets cohérents et ordonnés
- [ ] Les dépendances entre tickets sont correctement exprimées (le frontend dépend du backend)
- [ ] Les critères d'acceptation de chaque draft sont observables et testables
- [ ] Une description trop vague ("améliorer le truc") produit une réponse d'erreur ou des tickets très généraux indiquant que la description doit être précisée

## Spécifications techniques

Validation des `depends_on_index` :
- Pas de self-reference (`index i` ne peut pas dépendre de `i`)
- Pas d'out-of-bounds (l'index doit exister dans le tableau)
- Pas de cycles (détection par parcours DFS)

Le CLAUDE.md du projet est inclus dans le contexte pour que l'agent connaisse la stack et adapte les tickets.

## Dépendances

- **ticket-021** — `utils/json_extract` pour l'extraction JSON fiable.

## Estimation

**1j** — Service LLM + prompt engineering + validation des dépendances + tests.

## Risques

- **Moyen** — Qualité du découpage dépend de la description fournie. Des descriptions ambiguës peuvent produire des tickets trop gros ou mal ordonnés.
