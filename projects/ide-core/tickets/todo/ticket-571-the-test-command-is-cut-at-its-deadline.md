---
id: ticket-571
title: "The test command is cut at its deadline even when the event loop is busy"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
plan: true
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
appels synchrones pendant un run) et l'écrit dans son plan.

## Solution proposée
En plus du `wait_for`, un garde-fou indépendant de la boucle : un
`threading.Timer` armé à l'échéance, qui termine le groupe de processus de
l'étape (`GroupeDEtape`, ticket-507) s'il tourne encore. Le `TestResult`
renvoyé reste celui d'un délai expiré. Le minuteur est annulé quand l'étape
finit à temps.

## Critères d'acceptation
- [ ] Un test lance une commande qui dort plus longtemps que le délai, bloque la boucle d'événements par un appel synchrone, et vérifie que le processus est terminé au plus tard à l'échéance plus deux secondes
- [ ] Un test vérifie que le minuteur est annulé quand la commande finit avant l'échéance
- [ ] La ligne de `memory/pipeline-log.md` d'un délai expiré donne la durée réelle, et un test vérifie qu'elle ne dépasse pas le délai de plus de quelques secondes
- [ ] Un commentaire de `services/test_runner.py`, près du minuteur, dit pourquoi le `wait_for` seul ne suffit pas (une boucle d'événements bloquée ne déclenche pas son minuteur)

## Ce que ça ne fait pas
- Ne change pas `test_timeout_s` d'ide-core.
