---
id: ticket-1025
title: "Design: bring the cost of a call under the agent account back to a few seconds"
type: design
status: todo
pr_number: null
priority: high
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-19
---

# ticket-1025 — Conception : ramener le coût d'un appel sous le compte agent à quelques secondes

## Objectif

Choisir comment garder les fermetures des tickets 1006, 1008, 1014 et 1018
sans que chaque appel d'agent paie près d'une minute d'ouverture et de
clôture, puis écrire les tickets de réalisation.

## Contexte

Mesuré le 19/11 sur le poste, sous le compte agent, worktree de Serpent
(9 242 entrées avec `node_modules`), profil de 1 696 entrées :

| Étape | Durée |
|---|---|
| ouverture : `poser_ecriture` | 8,6 s |
| clôture : `retirer_les_taches` | 8,9 s |
| clôture : `arreter_les_restants` | 0,2 s |
| clôture : `reinitialiser_profil` | 8,8 s |
| clôture : `retirer_ecriture` | 31,3 s, dont 24,5 s pour le seul `/reset /T` |

Soit environ 58 s par appel. Un run de Serpent fait une dizaine d'appels
(installation, codeur, tests, audit, reviewer, validateur, documentation).
Le ticket-1022 a déjà regroupé les étapes d'une commande de tests sous un
seul appel (182 s → 89 s) ; les appels d'agent paient toujours plein tarif.

Les droits se propagent fichier par fichier (`icacls /T`), et le gros d'un
worktree est `node_modules`, que l'installation recrée à chaque run.

## Pistes à comparer

- **Un appel englobant par run** : le droit du compte reste posé du premier
  au dernier appel du run ; entre deux appels, seuls l'arrêt des processus
  restants et le profil se rejouent. Amende ADR-083 (le droit ne durait qu'un
  appel) : dire ce que cela ouvre si un processus survit entre deux appels.
- **Clôture légère entre deux appels, complète en fin de run** : retirer le
  droit sur la racine seule (sans `/T`) et reprendre propriété et héritage
  une fois, à la fin.
- **Ne reprendre que ce que le compte a créé** : lister les fichiers dont il
  est propriétaire au lieu de parcourir tout l'arbre.
- **Tâches planifiées** : les retirer en fin de run et au démarrage, pas à
  chaque appel.
- Un `/reset` qui ne coûte que lorsqu'il change quelque chose : mesurer une
  seconde clôture sans appel entre les deux.

## Ce qu'il faut produire

Une ADR au prochain numéro libre de `memory/decisions.md`, qui retient une
voie avec sa mesure attendue et ce qu'elle laisse ouvert, et les tickets de
réalisation dans `tickets/todo/`, chacun avec `preuve_reelle: true` et une
mesure à noter.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` compare au
  moins trois des pistes ci-dessus et en retient une.
- [ ] L'ADR dit, pour la voie retenue, ce qu'un processus du compte resté
  vivant entre deux appels pourrait faire, et par quoi c'est fermé.
- [ ] Chaque ticket de réalisation de `tickets/todo/` porte
  `preuve_reelle: true` et demande de noter la durée d'ouverture et de
  clôture mesurée.

## Ce que ça ne fait pas

- N'écrit aucun code.
- Ne retire aucune des fermetures existantes sans le dire dans l'ADR.
