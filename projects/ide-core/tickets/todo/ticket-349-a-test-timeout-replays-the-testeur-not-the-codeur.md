---
id: ticket-349
title: "A test timeout replays the testeur once instead of sending the ticket back to the codeur"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-348"]
estimated_days: 0.5
plan: true
created: 2026-10-05
---

# ticket-349 — Un timeout du testeur rejoue le testeur, pas le codeur

## Objectif

Qu'une suite de tests coupée par son délai ne soit plus lue comme des tests
rouges : elle n'a rien prouvé sur le code, et renvoyer le ticket au codeur
dépense un tour pour rien.

## Contexte

Sur timeout, `_executer` de `backend/src/tessera/services/test_runner.py`
rend un `TestResult(passed=False, output_summary="Timeout après …s — …")`.
`run_tests` de `backend/src/tessera/services/pipeline_stages.py` ne
distingue pas ce cas : il rend `False`, et l'orchestrateur relance le codeur
(« tests rouges au tour 1 »). Le 2026-10-05, le ticket-347 a ainsi perdu un
tour entier, puis son second codeur a tourné 846 s sur un code qui n'était pas
en cause.

Le cas voisin existe déjà : `demarree=False` distingue « la commande n'a pas
démarré » d'un test rouge (ticket-157). Le timeout mérite le même traitement.

## Solution proposée

1. `TestResult` gagne un champ `expiree: bool = False`, posé à `True` par la
   branche timeout de `_executer` et nulle part ailleurs.
2. Dans `run_tests` (`pipeline_stages.py`), un résultat `expiree` relance la
   suite **une fois**, sans repasser par le codeur, en écrivant
   `[ticket-XXX] testeur: délai dépassé, suite relancée` dans le
   `pipeline-log`.
3. Si la relance expire aussi, le run se termine en `blocked` avec la raison
   « testeur: délai dépassé deux fois » — commit compris, comme toute sortie
   (ADR-037). Le ticket n'est pas renvoyé au codeur et le tour n'est pas
   consommé.
4. Un vrai test rouge (`expiree` faux, `passed` faux) garde le comportement
   actuel.

## Critères d'acceptation

- [ ] `TestResult` porte `expiree`, et un test de `test_test_runner.py`
      vérifie qu'il vaut `True` sur timeout et `False` sur un échec ordinaire
- [ ] Un test du pipeline montre qu'un premier résultat `expiree` suivi d'un
      résultat vert enchaîne sur la sécurité sans relancer le codeur
- [ ] Un test montre que deux résultats `expiree` de suite terminent le run en
      `blocked`, avec la raison « délai dépassé deux fois », sans tour de
      codeur supplémentaire
- [ ] Un test montre qu'un résultat rouge non expiré renvoie toujours au
      codeur, comme avant
- [ ] La ligne « testeur: délai dépassé, suite relancée » apparaît dans le
      `pipeline-log` lors d'une relance

## Dépendances

ticket-348 (même fichier `test_runner.py`, et le créneau partagé rend la
relance utile : elle part avec la machine moins chargée).

## Estimation

Une demi-journée.

## Risques

Chercher où l'orchestrateur décide « tests rouges → codeur » avant de coder :
c'est le tour de plan qui doit le trouver, pas le codeur à l'aveugle.
