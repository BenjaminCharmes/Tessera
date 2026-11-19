---
agent: codeur
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1022
pr_number: 1199
preuve_reelle: true
priority: high
status: done
title: A test command opens one call for all its steps under the agent account
type: fix
---

# ticket-1022 — Une commande de test ouvre un seul appel pour toutes ses étapes

## Signalement

Serpent ticket-013, le 19/11, premier run avec les tickets 1006, 1008 et 1014
actifs : `testeur: délai dépassé (120 s, durée réelle 145 s) — typecheck
61 s, lint 39 s, npm 39 s, build coupé après 31 s`, puis suite relancée. La
veille, les mêmes étapes tenaient en une vingtaine de secondes.

## Contexte

Sous le compte agent, chaque étape de la commande de test
(`typecheck && lint && test && build`) passe par `lancer_sous_compte`, donc
ouvre puis clôt son propre appel (`services/verification/test_runner.py`,
`_executer`, par `GroupeDEtape.fermer_et_clore`). Depuis les tickets 1006,
1008 et 1014, clore le dernier appel d'un worktree coûte cher : propriété et
droits remis sur tout le worktree (8,9 s mesurées sur les 9 240 entrées de
Serpent), profil repris puis vidé. Quatre étapes paient quatre fois.

`_ACTIFS` (`services/providers/droits_appel.py`) compte déjà les appels par
racine : tant qu'un appel reste ouvert sur le worktree, clore les autres ne
fait que décrémenter.

## Ce qu'il faut faire

- `run_tests` de `test_runner.py` : quand le compte est déclaré
  (`compte_declare()`), ouvrir un appel sur le dossier des tests
  (`ouvrir_appel`) avant la première étape et le clore (`clore_appel`) dans un
  `finally` après la dernière, relances comprises. Les étapes gardent leur
  propre ouverture et leur propre clôture : elles ne font plus que compter.
- Le job de chaque étape se ferme toujours à la fin de l'étape : rien ne
  change pour l'arrêt des processus d'une étape.
- Un refus à la clôture finale (`DroitsAgentRefuses`) remonte comme
  aujourd'hui celui d'une étape : le run finit `blocked`.
- Sans compte déclaré, aucun appel n'est ouvert.

## Critères d'acceptation

- [ ] Test, compte déclaré, faux lanceur et faux `Icacls`, commande de trois
  étapes : `/setowner` sur le worktree est émis une seule fois, après la
  dernière étape.
- [ ] Test : une étape qui lève laisse quand même l'appel englobant se clore
  (aucune entrée restante dans `_ACTIFS`).
- [ ] Test : sans compte déclaré, `ouvrir_appel` n'est pas appelé par
  `run_tests`.

## Preuve réelle

Un run Serpent complet sous le compte : relever dans le journal la durée de
chaque étape du testeur, constater qu'aucun « délai dépassé » n'apparaît, et
noter les durées dans le ticket, à côté de celles du 19/11 ci-dessus.

## Ce que ça ne fait pas

- Ne regroupe pas les appels d'agent entre eux (codeur, reviewer…) : chacun
  reste un appel, avec sa clôture complète.
- Ne change pas le délai du testeur.