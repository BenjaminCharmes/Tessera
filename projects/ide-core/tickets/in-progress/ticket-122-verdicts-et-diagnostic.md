---
id: ticket-122
title: "Verdicts stricts, audit qui échoue fermé, logs qui gardent leur cause"
type: fix
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-22
---

# ticket-122 — Verdicts stricts, audit qui échoue fermé, logs qui gardent leur cause

## Objectif

Que les décisions du pipeline reposent sur des signaux fiables, et qu'une
panne soit diagnosticable.

## Contexte

- `_parse_reviewer_verdict` : `"APPROVED" in content.upper()` — « should not
  be approved » sans `CHANGES_REQUESTED` est lu comme approbation (ADR-009).
- `security_auditor` : provider indisponible → `PASS`, JSON illisible →
  `PASS`, exception dans l'étape → audit sauté. `has_critical` / `has_high`
  calculés mais ne gatent rien malgré la docstring. Le validateur, lui, rend
  `CHANGES_REQUESTED` sur JSON illisible mais `APPROVED` sur provider en
  panne.
- `utils/logger._JsonFormatter` ne sort que `level/logger/message/exc_info` :
  les ~80 `extra={"error": …}` du backend sont perdus. `ide_log_level` n'est
  pas lu.
- `pipeline_outcomes.py` interpole `run.ticket.title` brut dans le sujet du
  commit approuvé (un `title: >` multi-ligne coupe le sujet) ; `_single_line`
  existe déjà.
- `pipeline_stages.py` émet `agent=codeur` sur `AGENT_STARTED` / `AGENT_TOKEN`
  / `AGENT_TOOL_USE` même quand `architect` produit.
- `ticket_service.get_ticket` matche `path.stem.startswith(ticket_id)` :
  `ticket-1` trouve `ticket-100`. `rotate_pipeline_log` lit
  `project/pipeline-log.md` alors que l'orchestrateur écrit
  `project/memory/pipeline-log.md`.
- `test_runner` : après `proc.kill()` pas de `await proc.wait()` ; pytest exit
  5 (aucun test collecté) lu comme rouge.
- `ChatService(provider: object)` et `DocumentationService(provider: object)`
  forcent six `type: ignore[attr-defined]`.

## Solution proposée

1. Verdict : `re.search(r"\bAPPROVED\b", content)` sensible à la casse, sur
   une ligne qui ne contient pas `CHANGES_REQUESTED`.
2. Audit sécurité : provider indisponible ou JSON illisible → `BLOCK` avec
   `reason` explicite ; `has_critical or has_high` bloque. Validateur :
   provider en panne → `CHANGES_REQUESTED`. Les prompts ne changent pas.
3. Logger : sérialiser tous les attributs `extra` (clés hors
   `logging.LogRecord` standard) ; lire `settings.ide_log_level`.
4. `_single_line(run.ticket.title)` dans le sujet ; `agent=role` sur les
   quatre événements d'agent.
5. `get_ticket` : correspondance `stem == id or stem.startswith(id + "-")`.
   `rotate_pipeline_log` reçoit le chemin réel.
6. `test_runner` : `await proc.wait()` après `kill`, exit 5 → `passed=True`
   avec `tests_run=0` et un avertissement.
7. Typer `provider: LLMProvider` et `git_workspace: GitWorkspaceService | None`,
   supprimer les `type: ignore` correspondants.

Hors périmètre : découpage des fichiers > 200 lignes, dédoublonnage du
contexte projet, gestion de `CommitFailed` (ticket-121).

## Critères d'acceptation

- [ ] Test : « this should not be approved » → non approuvé ; « APPROVED »
      seul → approuvé ; « approved » minuscule → non approuvé
- [ ] Tests : auditeur sans provider → `BLOCK` ; JSON illisible → `BLOCK` ;
      un issue `HIGH` avec verdict `PASS` → bloque
- [ ] Test : un `_logger.warning("x", extra={"error": "boom"})` produit un JSON
      qui contient `"error": "boom"`
- [ ] Test : un titre sur deux lignes donne un sujet de commit sur une ligne
- [ ] Test : `get_ticket("ticket-1")` ne renvoie pas `ticket-100`
- [ ] Test : `rotate_pipeline_log` agit sur `memory/pipeline-log.md`
- [ ] `grep -rc "type: ignore" backend/src` : au plus 2 occurrences au total
- [ ] `uv run pytest -q` et `uv run mypy src/` verts

## Ce que ça ne fait pas

- Ne découpe pas les fichiers de plus de 200 lignes, ne dédoublonne pas le
  contexte projet, ne touche pas à `CommitFailed` (ticket-121).
- Un `type: ignore` subsiste : le `**kwargs` passé à `ClaudeAgentSDKProvider`
  dans `providers/__init__.py`. Le retirer demande de réécrire la fabrique.
- La lecture de l'exit 5 comme « aucun test » exige aussi la ligne
  `no tests ran` de pytest. Un autre lanceur qui sort 5 reste rouge.
- `rotate_pipeline_log` cible désormais `memory/pipeline-log.md` et accepte
  un chemin explicite, mais rien dans le backend ne l'appelle encore : la
  rotation n'est pas branchée à l'orchestrateur.
- Le `reason` de l'audit part dans `SECURITY_AUDIT_DONE` et dans le message du
  commit `chore: … unapproved work (security block: …)`. Aucun rendu dédié
  n'a été ajouté côté frontend : il s'affiche avec les données de l'événement.
- L'audit et la validation n'échouent fermés que sur les projets qui activent
  ces étapes ; sans critère d'acceptation, le validateur approuve toujours
  d'office. Le verdict du reviewer, lui, reste parsé par mot-clé (ADR-009).
- `ide_log_level` est lu à la création d'un logger, pas rechargé ensuite ; un
  `level` explicite passé à `get_logger` l'emporte.

## Dépendances
Aucune.

## Estimation
2 jours.

## Risques
Un auditeur qui échoue fermé bloque les runs quand le provider tombe : c'est
voulu, et le `reason` doit le dire à l'écran.
