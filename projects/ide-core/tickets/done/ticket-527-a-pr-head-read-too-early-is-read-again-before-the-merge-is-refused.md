---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-527
pr_number: null
priority: high
status: done
title: A pull request head that still shows the previous commit is read again for
  a short while before the merge is refused
type: fix
---

# ticket-527 — Une tête de PR lue trop tôt est relue avant de refuser le merge

## Objectif
Qu'une PR approuvée ne reste pas ouverte parce que l'API GitHub n'avait pas
encore pris en compte le dernier push, quelques secondes plus tôt.

## Contexte
Depuis le ticket-492, `CIWatcher._tete_changee`
(`backend/src/tessera/services/ci_watcher.py`) compare la tête de la PR, lue
sur GitHub, au commit que la livraison a poussé. En cas d'écart, il refuse
aussitôt, sans relire.

Le 19/10, ide-core ticket-517, PR #571 : le dernier commit de rangement
`eab7443` a été poussé à 18:26:37 UTC. Le contrôle a lu la tête à 18:26:43 et
GitHub a rendu `9c3e03e`, le commit précédent, qui fait pourtant partie de la
même branche. Le journal dit : « la tête de la PR #571 n'est plus le commit
poussé : 9c3e03e au lieu de eab7443. La PR reste ouverte. » Une minute plus
tard, la PR avait bien `eab7443` pour tête. Elle a été mergée à la main.

## Solution proposée
Quand la tête lue diffère du commit poussé ET que ce commit poussé descend de
la tête lue (la tête est simplement en retard), relire la tête plusieurs fois
pendant une courte fenêtre (par exemple 5 lectures sur 60 s). Ne refuser que
si, au bout de la fenêtre, la tête n'est toujours pas le commit poussé. Une
tête qui n'est PAS un ancêtre du commit poussé (quelqu'un a poussé autre
chose) refuse immédiatement, comme aujourd'hui. Si l'ascendance ne peut pas
se vérifier, relire quand même pendant la fenêtre, puis refuser.

## Critères d'acceptation
- [ ] Dans `ci_watcher.py`, une tête lue en retard puis à jour à la lecture suivante ne refuse pas le merge (un test le vérifie avec une fausse lecture qui renvoie d'abord l'ancien SHA)
- [ ] Un test vérifie qu'une tête restée différente jusqu'au bout de la fenêtre refuse le merge avec le message actuel
- [ ] Un test vérifie qu'une tête qui n'est pas un ancêtre du commit poussé refuse sans attendre
- [ ] La fenêtre de relecture est bornée et réglable, et les tests l'injectent courte, sans vrai `sleep`
- [ ] Les tests existants du CIWatcher passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Rester fermé (ADR-039) : la relecture ne fait que retarder le refus, elle ne
merge jamais une tête différente du commit poussé.