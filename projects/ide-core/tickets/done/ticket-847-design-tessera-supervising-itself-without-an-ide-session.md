---
agent: architect
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-847
pr_number: null
priority: high
status: done
title: Design Tessera supervising itself, without an IDE session next to it
type: design
---

# ticket-847 — Concevoir un Tessera qui se supervise lui-même, sans session d'IDE à côté

## Objectif

Benjamin peut tout faire depuis Tessera, sans passer par une session Claude Code dans VS Code :
ce qu'une telle session fait aujourd'hui en plus de Tessera devient une capacité de Tessera.

## Contexte

Benjamin, le 05/11 : « si un jour je ne veux plus du tout passer par VS Code mais tout faire
depuis Tessera ? C'est le but ultime de Tessera. » Aujourd'hui, une session Claude Code
« ide-core » tient, à côté de Tessera, un rôle que le produit n'a pas :

1. **Trier** les signalements (ticket-407, `routers/signalements.py`) : ils arrivent bruts
   (`- [ ] À écrire au triage`) ; la session les réécrit en vrais tickets (critères
   vérifiables, dépendances, portée).
2. **Valider** les leçons proposées (ADR-074) et les règles `## Proposées` (ADR-055) à la place
   de Benjamin, qui le lui a délégué le 05/11 (modèle fort pour les décisions sensibles ; récap
   à son retour ; restent à lui : argent, suppression, secrets, professionnel).
3. **Débloquer** : finir un ticket approuvé non livré, recoller un conflit de journaux ou de
   numérotation (05/11 : trois designs parallèles ont pris le même numéro d'ADR et de tickets),
   merger une PR verte oubliée par CIWatcher après une veille, comprendre une file interrompue.
4. **Faire communiquer les projets** : les sessions de projet signalent à la session ide-core
   les défauts de Tessera qu'elles rencontrent (messagerie entre sessions de Claude Code). Un
   agent de Tessera, lui, échoue sans rien signaler.
5. **Revoir un projet** sur demande (« relis Vigie et propose des changements ») : aucun rôle
   ne le fait ; `project-analyzer` n'écrit que le `CLAUDE.md` d'un projet importé.

Le détecteur d'anomalies (ADR-078) observe sans gouverner ; ce design décide ce qui, au-delà
de l'observation, peut agir, et dans quelles bornes.

## Ce que la conception doit fixer

- **Un rôle superviseur** : ce qu'il peut faire seul (trier un signalement en ticket, valider ou
  écarter une leçon ou une règle selon la délégation, relivrer, merger une PR verte dont la
  tête est `pushed_sha`, relancer une file interrompue par une veille), ce qu'il ne fait jamais
  (argent, suppression, secrets, professionnel, écriture de `agents.json`, `.github/`,
  `CLAUDE.md`), son modèle (fort pour les décisions sensibles), quand il tourne (événements,
  cadence), et où il rend compte (« À toi », récap daté, réversible).
- **Un outil `signaler` pour tout agent** : quand et comment un agent signale un défaut de
  Tessera rencontré (garde trop strict, outil cassé, consigne contradictoire) au backlog
  d'ide-core, borné en nombre et en taille, sans jamais fuiter de données d'un projet
  `professional` ni de secret.
- **Un mode « revue de projet »** : lancé depuis l'interface sur un projet ; produit des tickets
  pour ce projet et des signalements pour ide-core ; sans écrire de code ; coût plafonné.
- **La concurrence** : comment le superviseur, les files et CIWatcher ne se marchent pas dessus
  (RunLock, numérotation des ADR et des tickets entre designs parallèles).
- Les règles proposées sous `## Proposées` (ADR-055), y compris celles qui bornent le
  superviseur.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` répond à
      chacun des points ci-dessus et cite au moins trois incidents réels du 04 ou du 05/11
- [ ] Les règles nouvelles sont écrites sous `## Proposées` de
      `projects/ide-core/memory/contraintes.md`, avec l'ADR
- [ ] Les tickets d'implémentation sont créés dans `projects/ide-core/tickets/todo/`, chacun
      tient en moins d'une journée, nomme ses tests et déclare ses `depends_on`
- [ ] Aucun code n'est écrit par ce ticket

## Ce que ça ne fait pas

Aucun déploiement cloud ni multi-utilisateur (hors scope, `CLAUDE.md`). Le superviseur ne
remplace pas Benjamin sur les décisions qui lui restent.