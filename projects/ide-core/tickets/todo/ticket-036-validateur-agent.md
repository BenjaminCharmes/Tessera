---
id: ticket-036
title: "Agent validateur — vérification des critères d'acceptation"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-021
  - ticket-035
estimated_days: 1
created: 2026-06-21
---

# ticket-036 — Agent validateur

## Objectif

Garantir que chaque ticket livré satisfait réellement ses critères d'acceptation, pas seulement qu'il compile et que les tests passent. Le validateur lit le code produit, les critères du ticket, et rend un verdict critère par critère — le reviewer ne peut pas approuver si le validateur dit non.

## Contexte

Le reviewer valide la qualité technique du code. Le validateur a une responsabilité différente : vérifier que le comportement attendu (exprimé dans les critères d'acceptation du ticket) est effectivement implémenté. Ces deux vérifications sont orthogonales et doivent rester séparées.

### Pipeline cible
```
codeur → testeur → reviewer
                      ↓
                  validateur  (vérifie les critères d'acceptation)
                      ↓
                  APPROVED / CHANGES_REQUESTED
```

## Solution proposée

### `agents/prompts/validateur.md`

```markdown
Tu es un agent de validation fonctionnelle.
Tu reçois le ticket avec ses critères d'acceptation, le code produit, et le résultat des tests.

Pour chaque critère d'acceptation, détermine s'il est satisfait en te basant
sur le code (pas les tests — les tests peuvent mal couvrir le critère).

Réponds avec ce JSON :
{
  "all_passed": true,
  "criteria": [
    { "criterion": "Token Google validé", "passed": true, "note": "" },
    { "criterion": "Session créée", "passed": false,
      "note": "Session non persistée en base — seulement en mémoire" }
  ],
  "verdict": "APPROVED",
  "feedback": "Résumé en 2-3 phrases."
}
```

### `backend/src/vibe_ide/services/validator.py`

```python
@dataclass
class CriterionResult:
    criterion: str
    passed: bool
    note: str

@dataclass
class ValidationResult:
    all_passed: bool
    criteria: list[CriterionResult]
    verdict: Literal["APPROVED", "CHANGES_REQUESTED"]
    feedback: str

class ValidatorService:
    async def validate(
        self,
        ticket: Ticket,
        code_produced: str,
        test_result: TestResult | None,
    ) -> ValidationResult:
        # Appel Claude avec validateur.md
        # Extraire JSON via utils.json_extract
```

### Intégration dans `OrchestratorService`

```python
if pipeline_config.validateur_enabled:
    validation = await validator.validate(ticket, code, test_result)
    if validation.verdict == "CHANGES_REQUESTED":
        # Court-circuit : le reviewer ne peut pas approuver
        return PipelineResult(approved=False, reason=validation.feedback)
    # Sinon, passer le résultat de validation au reviewer
```

### Activation

```json
{ "pipeline": { "validateur_enabled": true } }
```

## Critères d'acceptation

- [ ] Chaque critère d'acceptation du ticket est évalué individuellement avec un verdict pass/fail
- [ ] Si un critère échoue, le verdict global est `CHANGES_REQUESTED` et le reviewer ne peut pas approuver
- [ ] Le feedback du validateur est visible dans l'`AgentPanel`
- [ ] Un ticket sans critères d'acceptation → verdict `APPROVED` automatique (pas de blocage)
- [ ] Désactivé par défaut — aucun impact sur les pipelines existants

## Spécifications techniques

Court-circuit de sécurité : si `ValidationResult.verdict == "CHANGES_REQUESTED"`, le reviewer reçoit le feedback mais ne peut pas retourner `APPROVED`. L'orchestrateur boucle pour un nouveau tour codeur.

Si le ticket n'a pas de critères d'acceptation (`ticket.acceptance_criteria == []`), retourner `APPROVED` sans appel LLM.

## Dépendances

- **ticket-021** — `utils/json_extract` pour l'extraction JSON.
- **ticket-035** — Le `TestResult` du testeur est passé au validateur comme contexte.

## Estimation

**1j** — Service LLM + intégration orchestrateur + tests critères pass/fail.

## Risques

- **Moyen** — Le validateur peut être trop strict sur des critères ambigus, bloquant des implémentations valides. Le prompt doit favoriser une interprétation raisonnable.
