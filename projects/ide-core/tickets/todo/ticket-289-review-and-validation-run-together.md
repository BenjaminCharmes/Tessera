---
id: ticket-289
title: "The reviewer and the validator judge the same diff concurrently"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-279"]
estimated_days: 1
created: 2026-10-01
plan: true
---

# ticket-289 — Reviewer et validateur jugent le même diff en parallèle

## Objectif

Gagner, à chaque tour, la durée de la plus courte des deux étapes, et donner
au codeur les deux avis à la fois quand le tour est refusé.

## Contexte

`_run_rounds` (`services/orchestrator.py:302-316`) enchaîne sécurité →
reviewer → validateur. Médianes mesurées le 2026-10-01 : sécurité 30 s,
reviewer 78 s, validateur 138 s (Ollama local, choix voulu).

Le validateur ne lit ni le verdict du reviewer ni l'audit : il reçoit les
critères, le diff et le résultat de tests (`run_validation`,
`services/pipeline_stages.py:509-544`). Rien ne l'oblige à attendre.

Le reviewer, lui, dépend de l'audit : les avertissements MEDIUM/LOW lui sont
transmis par `run.security_context`. La sécurité reste donc devant.

Aujourd'hui, un validateur qui refuse n'est consulté qu'après une approbation
du reviewer. Le codeur peut alors corriger le reviewer au tour 1 puis
découvrir le validateur au tour 2 : 28 % des tickets font deux ou trois tours.

## Solution proposée

- Après l'audit sécurité, `run_review` et `run_validation` partent ensemble
  (`asyncio.gather`). Un audit `BLOCK` termine le run comme aujourd'hui, sans
  lancer ni l'un ni l'autre.
- Le verdict ne change pas : approuvé seulement si le reviewer approuve **et**
  si le validateur ne refuse pas. Une exception de l'un ou de l'autre refuse,
  sans annuler l'autre étape (ADR-039).
- Sur un refus, `review_feedback` reçoit les motifs des deux étapes qui ont
  refusé, chacun nommant son auteur.
- L'instantané du run (`RunActif`, `services/run_registry.py:42`) gagne une
  liste `etapes_en_cours`, renseignée par `run_executor`. Le champ `etape`
  reste, avec la dernière étape démarrée, pour les clients qui le lisent.

## Critères d'acceptation

- [ ] Un test vérifie que le validateur démarre avant la fin du reviewer
      (deux faux agents qui s'attendent mutuellement aboutissent)
- [ ] Un test vérifie qu'un audit `BLOCK` ne démarre ni le reviewer ni le
      validateur
- [ ] Un test vérifie qu'un reviewer qui approuve et un validateur qui
      refuse donnent un tour refusé
- [ ] Un test vérifie qu'un tour refusé par les deux transmet au codeur les
      deux motifs, chacun avec son auteur
- [ ] Un test vérifie qu'un validateur qui lève refuse le tour, et que le
      reviewer va quand même au bout
- [ ] Un test vérifie que `en_dict()` contient `etapes_en_cours` avec
      `revue` et `validation` pendant que les deux tournent

## Ce que ça ne fait pas

- La sécurité ne passe pas en parallèle : le reviewer perdrait ses
  avertissements.
- Le frontend n'affiche pas encore deux étapes actives : c'est le
  ticket-290.

## Dépendances

ticket-279 modifie `pipeline_stages.py` en ce moment.

## Estimation

1 jour.

## Risques

- Un tour que le reviewer refuse consomme désormais un appel au validateur.
  Il tourne sur Ollama : le coût est du temps machine, pas du quota.
- Les événements `agent_started` (reviewer) et `validation_started` sont
  maintenant entrelacés : vérifier que `run_executor` ne suppose aucun ordre.
