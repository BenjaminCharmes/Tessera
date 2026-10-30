---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-675
priority: medium
status: done
title: One reader for the agents.json manifest
type: refactor
---

# ticket-675 — Un lecteur unique du manifeste `agents.json`

## Objectif
Remplacer les 30 `json.loads` de `agents.json` (21 fichiers, voir
`docs/audit/doublons.md` §1.1) par un lecteur unique : une lecture, un défaut
documenté par clef, une journalisation d'un manifeste illisible.

## Contexte
Seul `services/politique_run.py:125-182` mutualise quatre clefs. Les autres
lecteurs divergent sur l'échec : `None`, `[]`, objet par défaut, exception,
`except Exception: pass`. `git_link.py:199-211` écrit le manifeste sans verrou.

## Critères d'acceptation
- [ ] Un module unique porte la lecture du manifeste ; `grep -rn "agents.json" backend/src/tessera --include=*.py` ne trouve plus de `json.loads` ni de `read_text` appliqué à ce fichier hors de ce module et de l'écrivain
- [ ] L'écriture de `agents.json` (`git_link.py`, `_store_github_remote`) passe par ce même module, qui préserve les clefs qu'il ne connaît pas
- [ ] Un manifeste absent ou illisible rend le même défaut pour une clef donnée quel que soit l'appelant, et une lecture illisible se journalise une fois
- [ ] Un test par clef lue (`github_remote`, `github_sync.label_map`, `base_branch`, `autonomy`, `git_root`, `artifacts`, `captures`, `online`, `worktree`, `services`, `pipeline`) couvre : présente, absente, mauvais type, JSON invalide
- [ ] `uv run pytest` et `uv run mypy` passent sans test supprimé

## Ce que ça ne fait pas
- Ne change aucune valeur par défaut observable d'un appelant : un écart entre deux copies se relève dans la PR, il ne se tranche pas en silence
- Ne touche pas `models/agent.py` (schéma des agents) ni le format du fichier
- Ne traite pas `remontée vers le dépôt` (ticket-676)