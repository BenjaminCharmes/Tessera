---
agent: codeur
created: 2026-10-23
depends_on: []
estimated_days: 0.5
id: ticket-571
plan: true
pr_number: null
priority: high
status: done
title: The test command is cut at its deadline even when the event loop is busy
type: fix
---

# ticket-571 — La commande de test est coupée à son échéance

## Objectif
Qu'une `test_command` qui ne finit pas soit coupée à `pipeline.test_timeout_s`,
pas une heure plus tard.

## Contexte
Le 23/10, au tour 2 du ticket-569 (ide-core, `test_timeout_s: 1500`),
`memory/pipeline-log.md` dit : « ../scripts/verifier.py coupé après 2597 s »,
puis, à la relance, « coupé après 5710 s » : 2 h 30 perdues au lieu de 50 min.
La même branche passe ensuite en entier, en série, en 22 min (3 609 tests) :
le code n'était pas en cause.

`_executer_dans` (`services/test_runner.py`) borne la commande par
`asyncio.wait_for(proc.communicate(), timeout=restant)`. Ce minuteur vit dans
la boucle d'événements du backend : si la boucle est bloquée (un appel
synchrone, comme le `shutil.rmtree` du ticket-551), il ne se déclenche pas à
l'heure. Le tour de plan cherche la cause réelle (journal du backend, autres
appels synchrones pendant un run) et le dit dans la PR.

## Solution proposée
En plus du `wait_for`, un garde-fou indépendant de la boucle : un
`threading.Timer` armé à l'échéance, qui termine le groupe de processus de
l'étape (`GroupeDEtape`, ticket-507) s'il tourne encore. Le `TestResult`
renvoyé reste celui d'un délai expiré. Le minuteur est annulé quand l'étape
finit à temps.

## Critères d'acceptation
- [x] Un test lance une commande qui dort plus longtemps que le délai, bloque la boucle d'événements par un appel synchrone, et vérifie que le processus est terminé au plus tard à l'échéance plus deux secondes
- [x] Un test vérifie que le minuteur est annulé quand la commande finit avant l'échéance
- [x] La ligne de `memory/pipeline-log.md` d'un délai expiré donne la durée réelle, et un test vérifie qu'elle ne dépasse pas le délai de plus de quelques secondes
- [x] Un commentaire de `services/test_runner.py`, près du minuteur, dit pourquoi le `wait_for` seul ne suffit pas (une boucle d'événements bloquée ne déclenche pas son minuteur)

## Cause du 23/10

Livré à la main le 23/10 : les trois critères de code validés à chaque tour ; le
quatrième, dans sa première version, visait la description de la PR, que le
validateur ne peut pas voir.

Phrase de la description de la PR : « Cause du blocage du 23/10 : non trouvée ;
le journal n'en garde pas la trace, deux pistes restent ouvertes (appel
synchrone `rmtree`, veille Windows). »

**Cause non trouvée.** Ni les lignes « coupé après 2597 s » et « 5710 s » du
ticket-569, ni le journal du backend de ce jour ne sont lisibles depuis ce dépôt :
`memory/pipeline-log.md` ne porte aucune ligne `testeur` pour ce ticket.

Deux pistes restent ouvertes, aucune n'est confirmée :
- un appel synchrone qui a bloqué la boucle partagée : `shutil.rmtree` de
  `git_workspace/rebase.py`, `git_clone.py`, `temporary_worktree.py`,
  `project_removal.py` ;
- la veille Windows : `time.monotonic`, donc `wait_for` comme le minuteur, n'avance
  pas pendant la veille, et le garde-fou ne la couvre pas.

Ce que le ticket change pour la suite : la ligne du journal d'un délai expiré porte
désormais la durée réelle (`délai dépassé (1500 s, durée réelle 2597 s)`). Au
prochain cas, un écart entre les deux chiffres dira si la boucle a tenu l'échéance.
Si c'est la veille, la mesure devra passer par `time.time()`.

## Ce que ça ne fait pas
- Ne change pas `test_timeout_s` d'ide-core.
- Ne couvre pas la veille Windows : le minuteur se compte lui aussi en `time.monotonic`.