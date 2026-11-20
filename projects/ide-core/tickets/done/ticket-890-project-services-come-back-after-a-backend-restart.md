---
agent: codeur
created: 2026-11-09
depends_on: []
estimated_days: 1
id: ticket-890
plan: true
pr_number: 996
priority: high
status: done
title: Project services come back after a backend restart
type: feat
---

# ticket-890 — Les services d'un projet reviennent après un redémarrage du backend

## Objectif

Qu'un redémarrage de Tessera ne coupe pas en silence les services de projet
que l'utilisateur avait lancés : au démarrage, le backend relance ceux qui
tournaient, et l'état d'un service dit toujours pourquoi il ne tourne plus.

## Contexte

ADR-042 : les services déclarés dans `agents.json` sont des enfants du backend
et meurent avec lui ; le registre `ProcessRegistry`
(`backend/src/tessera/services/verification/process_registry.py`) vit en
mémoire et son docstring juge « inutile toute reprise après redémarrage ».

Ce 09/11, un redémarrage du backend à 09:02 UTC a tué les trois services
d'Affût (backend 8024, frontend, veille) et le service web de Kadoomi
(port 3201). Les deux sessions ont dû les relancer à la main. Après le
redémarrage, `GET /projects/kadoomi/services` donnait `en_cours=false`,
`pid=null`, `code_de_sortie=null`, `arrete_a_la_main=false` : rien ne distingue
un service jamais lancé d'un service tué par le redémarrage.

Avec une session Claude par projet qui s'appuie sur ces services toute la
journée, un redémarrage d'ide-core ne doit plus être un incident pour les
autres projets. Le registre reste en mémoire ; ce qui se persiste est
l'**intention** : « les services de ce projet doivent tourner ».

## Solution proposée

- Une table SQLite `services_demandes(project_id TEXT PRIMARY KEY, demande_le TEXT)`,
  dans un module du domaine le plus bas qui convient (respecter `ORDRE`
  de `test_domaines_services.py`). `POST /{project_id}/services/start` y écrit
  le projet ; `POST /{project_id}/services/stop` l'en retire.
- Dans le `lifespan` de `main.py`, après la reprise des runs orphelins, pour
  chaque projet de la table : relancer ses services par le même chemin que la
  route `start`. Un projet dont le chargement ou le lancement échoue est
  journalisé (`services_non_repris`) et retiré de la table ; il ne bloque ni
  le démarrage ni les autres projets.
- Aucune reprise pour un projet dont un service est déjà « lancé hors de
  Tessera » (`_refuser_si_deja_lance_hors_de_tessera` de `routers/services.py`) :
  le port est pris, on journalise et on passe.
- Une ADR au prochain numéro libre de `memory/decisions.md` amende ADR-042 :
  les processus restent des enfants du backend, mais l'intention de les faire
  tourner survit au backend.

## Critères d'acceptation

- [ ] `POST /{project_id}/services/start` enregistre le projet dans
      `services_demandes` ; `POST /{project_id}/services/stop` l'en retire ; un
      test par route le vérifie sur une base temporaire.
- [ ] Au démarrage, une fonction de reprise (nommée dans le diff, appelée depuis
      `lifespan`) relance les services de chaque projet de la table ; un test
      avec un `ProcessRegistry` doublé vérifie que `demarrer` est appelé une fois
      par projet enregistré, et jamais pour un projet absent de la table.
- [ ] Un projet dont la relance lève une exception est journalisé et retiré de
      la table, et les projets suivants sont quand même relancés ; un test le
      vérifie.
- [ ] Un projet dont un service est déjà lancé hors de Tessera n'est pas relancé ;
      un test le vérifie avec le port occupé par un double.
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` amende ADR-042
      et dit ce qui se persiste (l'intention) et ce qui ne se persiste pas (les
      processus).

## Dépendances

Aucune.

## Estimation

Un jour.

## Risques

Un service qui plante au démarrage de Tessera ne doit pas empêcher le backend
de servir : la reprise se fait après les reprises d'orphelins, chaque projet
sous son propre `try`, et le retrait de la table évite une boucle de plantage
à chaque démarrage.

## Ce que ça ne fait pas

- Ne retrouve pas un processus orphelin : les services restent des enfants du
  backend (ADR-042).
- Ne relance pas un service arrêté par `stop` ou mort de lui-même avant le
  redémarrage : seule l'intention « start sans stop » compte.
- Ne change pas le frontend : le bouton existant reflète l'état servi.