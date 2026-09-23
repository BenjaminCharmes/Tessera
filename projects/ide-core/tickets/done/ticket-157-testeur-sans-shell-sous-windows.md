---
id: ticket-157
title: "Le testeur ne sait pas lancer npm sous Windows"
type: fix
status: done
pr_number: 179
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-157 — Le testeur ne sait pas lancer `npm` sous Windows

## Objectif

Qu'un projet dont `test_command` commence par `npm` voie ses tests exécutés,
au lieu d'un échec qui bloque chacun de ses tickets.

## Contexte

Trouvé au **premier ticket** du projet démineur (ticket-136), et il rendait
les vingt injouables. Les deux tours de revue ont échoué sur la même ligne :

```
testeur: Erreur d'exécution : [WinError 2] Le fichier spécifié est introuvable
```

`TestRunnerService` fait `shlex.split(cmd)` puis `create_subprocess_exec`.
Sans shell, `npm` ne se résout pas sous Windows : l'exécutable réel est
`npm.cmd`, et seul un shell applique `PATHEXT`.

C'est **exactement** le défaut corrigé dans `ProcessRegistry` au ticket-149,
par une reprise en `.cmd` au lancement. La correction n'a pas été portée ici.
Les deux classes font pourtant la même chose : lancer un processus déclaré
par un projet, sans shell, pour ne pas rouvrir ce qu'ADR-027 et ADR-031
ferment. Une seule sait le faire sous Windows.

C'est la forme d'ADR-034 prise par l'autre bout : non pas une règle décrite à
deux endroits, mais un **comportement implémenté** à deux endroits, corrigé à
un seul.

## Conséquence observée

Le ticket est rendu `blocked` alors que le code produit était juste. Rien à
l'écran ne distingue « le codeur s'est trompé » de « l'outil qui devait le
juger n'a pas démarré » : le verdict affiché est `changes requested`.

C'est le même reproche qu'ADR-039 adresse aux portes qui ne peuvent pas
juger — sauf qu'ici la porte échoue fermé correctement, mais sans dire que
c'est elle qui est en panne.

## Solution proposée

Porter la reprise de `ProcessRegistry` dans `TestRunnerService`, **sans la
réécrire une seconde fois** : l'extraire là où les deux peuvent l'appeler.
Deux copies de cette logique divergeraient exactement comme celles-ci
viennent de le faire.

Et distinguer, dans ce que le testeur rend, « la commande n'a pas pu
démarrer » de « les tests ont échoué ». Les deux ne demandent pas la même
chose au codeur, qui a passé deux tours à corriger du code qui n'était pas en
cause.

## Critères d'acceptation

- [ ] Un `test_command` commençant par `npm` s'exécute sous Windows
- [ ] La logique de résolution est écrite **une fois**, appelée par
      `ProcessRegistry` et `TestRunnerService`
- [ ] Un test couvre le cas d'une commande introuvable, et vérifie qu'elle
      est rendue comme « commande non démarrée », pas comme « tests rouges »
- [ ] Le message remonté à l'écran nomme la commande qui n'a pas démarré
- [ ] Rejouer `ticket-001` du projet démineur atteint le testeur

## Dépendances

Aucune. **Bloque** l'exercice du ticket-136 en entier.

## Estimation

Moins d'une journée.

## Risques

La résolution `.cmd` ne doit pas devenir une ouverture de shell : c'est
précisément ce qu'ADR-027 et ADR-031 évitent. On résout un exécutable, on
n'interprète pas une ligne de commande.
