---
id: ticket-515
title: "A project declares its worktree in agents.json, and the run policy freezes it"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-19
pr_number: null
---

# ticket-515 — Le projet déclare son worktree, la politique du run le fige

## Objectif
Que la clé `worktree` d'`agents.json` se lise **une fois**, avec le reste de
`PolitiqueRun`, et se valide avec des défauts fermés. Aucun comportement ne
change : personne ne consomme encore cette valeur.

## Contexte
ADR-056 et `docs/superpowers/specs/2026-10-19-worktree-par-run-design.md`
(§ 2). `PolitiqueRun` (`services/politique_run.py`) fige la politique avant le
premier agent (ticket-119) : la copie du worktree, que le codeur peut éditer,
ne doit jamais être relue.

## Ce qu'il faut faire
- `backend/src/tessera/models/worktree_config.py` : `EntreePopulate`
  (`path`, `mode: Literal["copy","link"]`) et `ConfigWorktree` (`populate`,
  `env`, `test_command`), `frozen`, signatures de la spec.
- `PolitiqueRun.worktree: ConfigWorktree | None`, lu par `PolitiqueRun.lire`.
  `None` : clé absente, illisible ou mal typée.
- Une entrée est **retirée et journalisée** si son `mode` est inconnu, si son
  chemin est absolu, contient `..`, ou résout au `.env` de Tessera (ADR-053).
  Les autres entrées valides sont conservées.
- Réglage `ide_worktrees_dir: Path` dans `config.py`
  (`IDE_WORKTREES_DIR`, défaut `Path.home() / ".tessera" / "worktrees"`).
- Un projet en `artifacts: local` qui déclare `worktree` : `PolitiqueRun.worktree`
  reste `None` et la raison est journalisée (la spec, « Ce que ça ne tranche
  pas »).

## Tests
Dans `backend/tests/test_politique_run.py` :
- [ ] clé absente → `worktree is None`
- [ ] clé valide → `ConfigWorktree` avec ses entrées, `env` et `test_command`
- [ ] `mode` inconnu, chemin absolu, chemin avec `..`, chemin du `.env` de
      Tessera → entrée retirée, les autres gardées
- [ ] `agents.json` illisible → `None`
- [ ] `artifacts: local` + `worktree` → `None`
- [ ] `ConfigWorktree` est immuable

## Critères d'acceptation
- [ ] `PolitiqueRun.lire` renvoie la configuration validée ou `None`
- [ ] Les six tests ci-dessus existent et passent
- [ ] Aucun service n'utilise encore `worktree` : le comportement des runs est inchangé
- [ ] mypy et la suite backend passent

## Dépendances
Aucune.

## Ce que ça ne fait pas
Ni création de worktree, ni peuplement : tickets 516 et 517.
