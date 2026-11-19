---
id: ticket-1012
title: "A reused parent PID no longer makes a system process a descendant of the account"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
created: 2026-11-19
---

## Signalement

- Source : agent:codeur@ticket-1006, le 19/11 (run `42abe3ec`, bloqué après
  trois tours de tests rouges sans lien avec son diff).
- `test_the_current_process_is_found_under_its_own_account` et
  `test_a_real_listing_refuses_nothing_on_a_healthy_machine` lèvent
  `ProcessusIllisibles` pour `csrss.exe`, `winlogon.exe`, `fontdrvhost.exe`
  et `dwm.exe`.

## Contexte

Relevé sur le poste : `csrss.exe` et `winlogon.exe` de la session 1, créés à
08:55:34, portent le PID de parent 1768. Ce parent est mort, et Windows a
réattribué le 1768 à `wslhost.exe`, créé à 08:56:45 sous le compte de
l'utilisateur. La filiation Toolhelp du ticket-997 ne connaît que des
numéros : elle rattachait ces processus système à un « parent » né après eux.

En test, le compte interrogé est celui de l'utilisateur : la suite backend
échouait jusqu'au prochain redémarrage du poste, et chaque run ide-core se
bloquait au testeur. En production, le même hasard sur le PID du backend ou
d'un processus du compte agent aurait bloqué tous les runs sous le compte.

## Ce qui a été fait

`services/providers/parentes_processus.py` :

- `naissances()` lit la date de création de chaque processus par
  `NtQuerySystemInformation`, sans en ouvrir aucun.
- `liens_vivants()` retire un lien dont le parent est né après l'enfant.
  Un lien dont une date manque reste : l'inconnu reste suspect.
- `parents_toolhelp()` rend la filiation filtrée ; ses deux sources
  s'injectent pour les tests.

Fait à la main par la session ide-core : le défaut bloquait le testeur de
tous les runs du projet.

## Critères d'acceptation

- [x] Test : un lien vers un PID de parent réattribué (parent né après
  l'enfant) est retiré, les autres liens restent.
- [x] Test : un lien sans ses deux dates reste.
- [x] Test (Windows) : la date de création du processus courant suit celle
  de son parent.

## Preuve réelle

Faite le 19/11 sur le poste, dans l'état qui produisait l'échec (PID 1768
réattribué) : `tests/test_processus_compte.py` passait de 2 échecs à 0, sans
modifier ce fichier.

## Ce que ça ne fait pas

- Ne change pas la règle du ticket-997 : un processus illisible qui descend
  vraiment du backend ou du compte reste refusé.
- Ne remplace pas Toolhelp comme source des liens.
