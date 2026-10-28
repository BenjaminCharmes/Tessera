---
id: ticket-605
title: "A script measures the input tokens per role and what headroom removes from them"
type: chore
status: todo
priority: low
agent: codeur
depends_on: [ticket-604]
estimated_days: 1
created: 2026-10-27
plan: true
---

# ticket-605 — Mesurer ce que headroom retire des entrées des agents

## Objectif
Produire les chiffres que ticket-589 n'a pas pu lire, pour rouvrir ou clore
ADR-063.

## Contexte
`docs/superpowers/specs/2026-10-27-compression-contexte-design.md`, sections 1
et 2. Rien n'est mesuré : ni les tokens d'entrée par rôle, ni ce que headroom
retire des diffs et des sorties de tests. Le ticket interdisait de modifier les
dépendances du backend : le script tourne donc hors de `backend/pyproject.toml`
(`uv run --with headroom-ai`, environnement jetable).

## Solution proposée
`scripts/mesurer_compression.py`. Il lit `agent_calls` (chemin de
`ide_db_path`) pour au moins deux runs d'ide-core dont un a un tour de test
rouge, somme par rôle `input_tokens`, `cache_read_tokens` et
`cache_creation_tokens`, puis rejoue headroom sur les mêmes textes : le diff du
run (`git diff` de sa branche mergée) et la sortie de `scripts/verifier.py`
(sur un worktree jetable avec un test volontairement rouge). Il écrit le
tableau dans la section 1 de la spec ci-dessus et dit « non mesuré » pour toute
cellule dont il n'a pas la donnée.

## Critères d'acceptation
- [ ] Le tableau de la spec donne, pour au moins deux runs réels et chaque rôle qui appelle un modèle, les tokens d'entrée mesurés et ceux après compression, ou « non mesuré » avec la raison
- [ ] Le script vérifie que chaque ligne `FAILED` et chaque nom de test de `extract_errors` / `extract_failure_details` figure encore dans le texte compressé, et le tableau donne le nombre de lignes perdues ; la fonction qui compare est testée avec un cas où une ligne manque
- [ ] La spec dit si `ResultMessage.usage` cumule les tokens des tours de la boucle d'outils, avec la ligne de sortie qui le montre
- [ ] `backend/pyproject.toml` et `uv.lock` sont inchangés
- [ ] La spec se conclut par une ligne : adopter / reporter / écarter, avec le seuil de réouverture de la section 4 appliqué aux chiffres obtenus (l'ADR qui en découle reste à écrire par un architecte)

## Ce que ça ne fait pas
- N'ajoute aucun module de compression au pipeline.
- Ne modifie aucun prompt.
