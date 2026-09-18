---
id: ticket-088
title: "Le périmètre d'écriture couvre aussi les redirections shell"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-087]
estimated_days: 1
created: 2026-09-18
---

# ticket-088 — `Bash` et le périmètre

## Pourquoi

ticket-085 ferme `Write`, `Edit` et `NotebookEdit` hors projet. `echo x >
../autre-client/app.py` passait toujours.

## Ce que j'avais recommandé, et pourquoi j'ai changé

J'avais proposé de **retirer `Bash` au codeur** et de ne le laisser qu'au
testeur. En vérifiant, le testeur n'est pas un agent : `TestRunnerService`
lance un sous-processus directement. La recommandation reposait donc sur une
hypothèse fausse, et retirer `Bash` au codeur lui aurait coûté son seul moyen
de vérifier son propre travail — pour fermer une porte que personne ne pousse.

Le vrai risque ici n'est pas l'évasion, c'est **l'erreur** : un agent qui se
trompe de projet. Et une erreur prend les formes simples.

## Critères d'acceptation

- [x] `>`, `>>` et `tee` vers un chemin hors périmètre sont refusés
- [x] La ligne est **tokenisée** : `grep -r 'x > y' src/` ne redirige rien
- [x] `2>&1` et `> /dev/null` ne sont pas des fichiers du projet
- [x] Un guillemet non fermé ne produit aucune cible — on n'invente pas
- [x] Les commandes de test courantes passent intactes
- [x] Le matcher du hook couvre `Bash`

## Ce que ça ne fait pas

**Ce n'est pas une frontière contre quelqu'un qui cherche à passer.**
`python -c "open('../x','w')"` écrit toujours où il veut. Le prétendre
reviendrait à mentir sur ce que ce module garantit : il attrape une erreur,
il n'arrête pas une intention.
