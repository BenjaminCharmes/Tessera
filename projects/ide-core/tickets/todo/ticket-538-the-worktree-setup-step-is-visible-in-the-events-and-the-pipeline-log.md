---
id: ticket-538
title: "The worktree setup step is visible in the events and the pipeline log"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-22
---

# ticket-538 — La préparation du worktree se voit dans les événements et le journal

## Objectif
Qu'on puisse dire, en lisant un run, si la préparation déclarée
(`worktree.setup`, ticket-536) a tourné, combien de temps, et avec quel code de
sortie.

## Contexte
Signalé par Kadoomi le 22/10 (run b95d446c, ticket-094). La préparation a
manifestement tourné (1 min 49 entre `branch_created` et le premier tour du
codeur, la durée d'un `pnpm install`), mais rien ne le nomme : aucun événement,
aucune ligne dans `memory/pipeline-log.md`. `services/preparation_worktree.py`
ne journalise que l'échec (`worktree_setup_echoue`), et seulement dans les logs
du backend.

## Solution proposée
Après la commande `setup`, que le résultat soit un succès ou un échec : un
événement d'orchestrateur `worktree_setup` (commande, durée en ms, code de
sortie) et une ligne dans le journal du pipeline, du même format que celles du
testeur. Sans `setup` déclaré, ni événement ni ligne.

## Critères d'acceptation
- [ ] Un type d'événement `worktree_setup` existe, et `services/preparation_worktree.py` l'émet après la commande avec la commande, la durée et le code de sortie
- [ ] La même étape écrit une ligne `[ticket-XXX] préparation: …` dans le journal du pipeline du run
- [ ] Un test vérifie, avec des doubles, l'événement et la ligne pour une préparation réussie
- [ ] Un test vérifie l'événement et la ligne pour une préparation en échec, avant le `blocked`
- [ ] Un test vérifie qu'un projet sans `setup` n'émet ni l'un ni l'autre
