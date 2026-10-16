---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-464
estimated_days: 1.5
id: ticket-465
priority: high
status: todo
title: A provisioning plan runs ordered steps, re-reads the world on every relaunch
  and creates only what is missing
type: feat
---

# ticket-465 — Orchestration et reprise de la mise en ligne

## Objectif

Le moteur commun des étapes de mise en ligne : leur contrat, leur ordre, la
déclaration `online` d'`agents.json`, la reprise sans état local.

## Contexte

ADR-053, section « Mise en ligne » de `docs/architecture.md`. Le monde (les
services eux-mêmes) est la source de vérité : aucun fichier d'état, comme les
tickets restent lisibles sans l'IDE. Les tickets 466 à 470 branchent chacun un
service sur ce moteur.

## Solution proposée

Package `services/provisioning/` (identifiants en anglais, ADR-044).

```python
class StepState(StrEnum):  # todo (lecture seule), done, skipped, pending,
    ...                    # manual, needs_human, failed

@dataclass(frozen=True)
class StepResult:
    state: StepState
    detail: str            # nom de ressource, instruction ; jamais une valeur secrète

class ProvisioningStep(Protocol):
    name: str
    async def inspect(self, ctx: ProvisioningContext) -> StepResult: ...  # lit seulement
    async def apply(self, ctx: ProvisioningContext) -> StepResult: ...    # crée le manquant
```

- `ProvisioningContext` : `project_id`, `online: OnlineConfig`,
  `env_writer` (`has_env(name)`, `set_env(name, value)` — branché par le ticket
  466), `wanted_dns: list[DnsRecord]`, `changed_env: set[str]`,
  `dns_published: bool`.
- `OnlineConfig` (Pydantic v2) lit le bloc `online` d'`agents.json` :
  `domain`, `resources` (valeurs connues seulement), et `stripe` (ticket 470).
- `ProvisioningPlan.run(ctx, dry_run)` : pour chaque étape, `inspect` ; `skipped`
  → suivante ; sinon `apply` (jamais en `dry_run`, qui rend `todo`). `failed` ou
  `needs_human` arrête les suivantes ; ce qui est fait reste fait.
- `ServiceError(service, status, code)` : message réduit au statut HTTP et au
  code d'erreur de l'API, jamais son corps.
- Événement `provisioning_step` (`step`, `state`, `detail`) sur le canal
  d'ADR-041.

## Critères d'acceptation

- [ ] Un test vérifie que les étapes s'exécutent dans l'ordre déclaré et que
      `failed` ou `needs_human` arrête les suivantes sans défaire les précédentes
- [ ] Un test vérifie que, le monde étant complet (`inspect` rend `skipped`
      partout), aucun `apply` n'est appelé et chaque étape émet `skipped`
- [ ] Un test vérifie que `dry_run` n'appelle jamais `apply` et rend `todo`
      pour ce qui manque
- [ ] Un test vérifie qu'un bloc `online` invalide (domaine absent, ressource
      inconnue) est refusé en nommant le champ, et qu'un bloc absent rend `None`
- [ ] Un test vérifie que `str(ServiceError)` ne contient pas le corps de la
      réponse, même quand ce corps répète un secret
- [ ] Un test vérifie qu'aucun événement `provisioning_step` ne contient la
      valeur d'un secret inscrit dans `SecretRegistry`

## Ce que ça ne fait pas

N'appelle aucun service réel : les tests utilisent des étapes factices.

## Dépendances

ticket-464 (`SecretRegistry`).
