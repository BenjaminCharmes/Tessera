---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 1
id: ticket-510
pr_number: null
priority: medium
status: done
title: Pull requests left to the CI watcher are watched again after a backend restart
type: feat
---

# ticket-510 — Les PR confiées au CIWatcher sont resurveillées après un redémarrage

## Objectif
Qu'un redémarrage du backend ne laisse plus une PR approuvée et verte sans
merge : à son démarrage, le backend reprend la surveillance des PR que le
CIWatcher suivait.

## Contexte
La phase 2 de livraison (attente de CI, merge) tourne dans `CIWatcher`
(`backend/src/tessera/services/ci_watcher.py`), en mémoire, en arrière-plan
(ADR-051). Un redémarrage coupe cette tâche, et rien ne la relance :
`reprise_orphelin.py` ne traite que les runs ouverts, pas les livraisons en
attente. Le 19/10 à 11:00 UTC, la PR #60 de Devinoo (ticket-030), confiée au
CIWatcher à 10:57, est restée ouverte après un redémarrage, avec une CI
verte : la session Devinoo l'a mergée à la main. Comme le backend redémarre
plusieurs fois par jour pour activer les correctifs, chaque fois une PR peut
rester sans merge.

## Solution proposée
Au démarrage, après la reprise des runs orphelins, pour chaque projet dont
l'autonomie est `merge` : retrouver les PR qui ont été confiées au CIWatcher
et n'ont ni été mergées ni été bloquées. Source suggérée : les tickets en
`in-review` qui portent un `pr_number`, croisés avec l'état de la PR sur
GitHub. Une PR encore ouverte est confiée de nouveau à `CIWatcher.surveiller`.
Une PR déjà mergée met le ticket à jour, comme un merge vu par le CIWatcher.
Une PR fermée sans merge ne fait rien, et une ligne le dit dans
`memory/pipeline-log.md`. Une PR issue d'une résolution de conflit (ADR-033)
ne se merge jamais seule : elle n'est pas reprise.

## Critères d'acceptation
- [ ] Un test vérifie qu'au démarrage, un ticket `in-review` avec un `pr_number` dont la PR est ouverte, sur un projet en autonomie `merge`, est confié à `CIWatcher.surveiller`
- [ ] Un test vérifie qu'une PR déjà mergée fait passer le ticket en `done` sans surveillance
- [ ] Un test vérifie qu'un projet en autonomie `commit` ou `pr` n'est jamais repris
- [ ] Un test vérifie qu'une PR fermée sans merge n'est pas reprise, et qu'une ligne est écrite dans `pipeline-log.md`
- [ ] Une erreur de lecture GitHub pendant cette reprise est journalisée et n'empêche pas le démarrage du backend (un test le vérifie)
- [ ] Chaque PR reprise écrit une ligne `[<projet>] ticket-XXX PR #N reprise par le CIWatcher après redémarrage` dans `memory/pipeline-log.md`

## Dépendances
Aucune.

## Estimation
Un jour.

## Risques
Ne jamais merger ce que le CIWatcher n'aurait pas mergé : la reprise passe par
`surveiller`, avec les mêmes règles (CI verte, `merge_without_ci`, tête de
branche inchangée).