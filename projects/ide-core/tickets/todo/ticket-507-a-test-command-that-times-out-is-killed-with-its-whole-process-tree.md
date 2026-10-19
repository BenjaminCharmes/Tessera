---
id: ticket-507
title: "A test command that times out is killed with its whole process tree, so the run never waits on a surviving grandchild"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-19
---

# ticket-507 — Une commande de test expirée est tuée avec tout son arbre de processus

## Objectif
Qu'un `test_timeout_s` dépassé termine toujours l'étape de test : le run
reprend la main, au lieu d'attendre indéfiniment un petit-enfant qui a survécu.

## Contexte
Le 19/10, la file Devinoo est restée figée 70 minutes sur ticket-024, alors que
le projet déclare `test_timeout_s: 420`. Sa `test_command` commence par
`corepack pnpm@10 install`, dont le postinstall lance `prisma generate` via
`sh`. Ce `prisma generate` s'est figé. À l'expiration, `TestRunnerService._executer`
(`backend/src/tessera/services/test_runner.py`) appelle `proc.kill()` puis
`await proc.wait()`. Sous Windows, `kill()` ne termine que le processus direct :
`corepack` et `prisma` ont survécu en gardant les tubes stdout/stderr ouverts,
et `proc.wait()` n'est jamais revenu. Il a fallu arrêter `prisma` à la main.

Les services, eux, ont déjà la parade : `groupe_de_processus.py` (tickets 150 et
153) met chaque service dans un job Windows `KILL_ON_JOB_CLOSE`, que toute la
descendance hérite, et `tuer_l_arbre` sert sous Unix (groupe de processus).
Le lanceur de tests ne s'en sert pas.

## Solution proposée
- Dans `test_runner.py`, chaque étape lancée par `_lancer` est rattachée à un
  groupe neuf (`creer_groupe` + `rattacher_au_groupe` sous Windows ; sous Unix,
  lancement avec `start_new_session=True`).
- À l'expiration : tuer tout le groupe (fermer le job, ou `tuer_l_arbre`),
  puis attendre la fin du processus avec un délai borné (quelques secondes).
  Passé ce délai, l'étape rend quand même son `TestResult(expiree=True)` :
  aucune attente non bornée ne reste après un timeout.
- Un groupe indisponible (le job ne se crée pas) retombe sur le comportement
  actuel, journalisé, sans faire échouer l'étape.

## Critères d'acceptation
- [ ] Dans `test_runner.py`, l'expiration d'une étape termine toute sa descendance : un test lance une commande qui démarre un petit-enfant de longue durée gardant stdout ouvert, avec un timeout court, et vérifie que `run_tests` rend un résultat `expiree=True` en moins de 30 secondes
- [ ] Ce même test vérifie que le petit-enfant n'est plus vivant après le retour de `run_tests`
- [ ] Après `proc.kill()`, l'attente de fin de processus dans `_executer` est bornée par un délai : un test où `wait()` ne revient jamais (faux processus) obtient quand même `expiree=True`
- [ ] Quand `creer_groupe` renvoie `None`, l'étape s'exécute normalement et un test le couvre
- [ ] Une commande qui finit dans le délai garde exactement son comportement actuel (code de sortie et sortie capturée) : les tests existants de `test_runner` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Un jour.

## Risques
Le job Windows d'un test ne doit pas être celui du backend (`_job`, tué à la
fermeture du backend) : un groupe par étape, fermé à la fin de l'étape, même
en cas de succès.
