---
id: ticket-037
title: "Agent sécurité — audit automatique des vulnérabilités OWASP"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on:
  - ticket-021
estimated_days: 1.5
created: 2026-06-21
---

# ticket-037 — Agent sécurité

## Objectif

Bloquer automatiquement la livraison de code contenant des vulnérabilités critiques (injection SQL, secrets exposés, path traversal…). L'agent `securite` audite le code avant le reviewer — si une vulnérabilité CRITICAL ou HIGH est détectée, le pipeline s'arrête et le ticket passe en `blocked`.

## Contexte

Aucun contrôle de sécurité n'est effectué aujourd'hui sur le code produit par le codeur. Ce ticket ajoute une gate de sécurité automatique, inspirée des security reviewers des CI/CD modernes. Elle est activable par projet.

### Pipeline cible
```
codeur → testeur → securite → reviewer → validateur → [doc-updater]
              ↓ BLOCK
         ticket = blocked
```

## Solution proposée

### `agents/prompts/securite.md`

```markdown
Tu es un expert en sécurité logicielle (OWASP Top 10, CVE).
Tu reçois le code produit par le codeur.

Cherche activement :
- Injection (SQL, commande OS, LDAP)
- XSS et injection HTML
- Secrets hardcodés (clés API, mots de passe, tokens)
- Path traversal
- Authentification/autorisation manquante
- Désérialisation non sécurisée
- Dépendances vulnérables (si package.json/requirements.txt modifiés)

Classe chaque problème : CRITICAL / HIGH / MEDIUM / LOW / INFO.
Verdict : BLOCK si CRITICAL ou HIGH, PASS sinon.

Réponds avec ce JSON :
{
  "issues": [
    {
      "severity": "HIGH",
      "type": "SQL Injection",
      "location": "src/db.py:42",
      "description": "...",
      "fix": "Utiliser des paramètres préparés"
    }
  ],
  "verdict": "PASS",
  "summary": "Aucune vulnérabilité critique détectée."
}
```

### `backend/src/vibe_ide/services/security_auditor.py`

```python
@dataclass
class SecurityIssue:
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    type: str
    location: str
    description: str
    fix: str

@dataclass
class SecurityAuditResult:
    issues: list[SecurityIssue]
    verdict: Literal["PASS", "BLOCK"]
    summary: str
    has_critical: bool
    has_high: bool

class SecurityAuditorService:
    async def audit(
        self,
        code_diff: str,
        project_path: Path,
    ) -> SecurityAuditResult: ...
```

### Comportement de blocage dans `OrchestratorService`

```python
if pipeline_config.securite_enabled:
    audit = await security_auditor.audit(code_diff, project_path)
    await emit_ws("security_audit_done", { "verdict": audit.verdict, ... })
    if audit.verdict == "BLOCK":
        await ticket_svc.update_status(ticket_id, TicketStatus.blocked)
        return PipelineResult(approved=False, reason=f"Bloqué sécurité: {audit.summary}")
    # Sinon, transmettre au reviewer avec le rapport comme contexte
```

### WS Events

- `security_audit_started`
- `security_audit_done` : `{ verdict, issues_count, has_critical, summary }`

Badge dans `TicketCard` : `⚠ BLOQUÉ (sécurité)` en rouge si verdict BLOCK.

### Activation

```json
{ "pipeline": { "securite_enabled": false } }
```

## Critères d'acceptation

- [ ] Un code avec une injection SQL détectée → verdict `BLOCK`, ticket passe en `blocked`
- [ ] Un code avec une vulnérabilité MEDIUM → verdict `PASS`, avertissement transmis au reviewer
- [ ] L'event WS `security_audit_done` apparaît dans l'AgentPanel avec le verdict
- [ ] Le badge `⚠ BLOQUÉ` est visible dans `TicketCard` si verdict BLOCK
- [ ] Désactivé par défaut — aucun impact sur les pipelines existants

## Spécifications techniques

MEDIUM et LOW ne bloquent pas mais sont inclus dans le contexte du reviewer pour information. Seuls CRITICAL et HIGH déclenchent `BLOCK`.

Activer `cache_control: ephemeral` sur le system prompt (invoqué à chaque round).

## Dépendances

- **ticket-021** — `utils/json_extract` pour l'extraction JSON. L'agent `securite` est enregistré dans le registre.

## Estimation

**1.5j** — Service audit + prompt engineering + intégration orchestrateur + tests BLOCK/PASS + events WS.

## Risques

- **Moyen** — Faux positifs possibles (signal BLOCK sur du code légitime). Le prompt doit prioriser la précision sur le recall pour éviter de bloquer des pipelines valides.
- **Faible** — Le blocage peut frustrer si trop de faux positifs. Prévoir un mode `warn_only` pour les projets qui veulent juste les avertissements.
