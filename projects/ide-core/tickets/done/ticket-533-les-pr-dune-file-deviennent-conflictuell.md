---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-533
priority: medium
status: done
title: Les PR d'une file deviennent conflictuelles sur la doc du pipeline quand la
  précédente est mergée après coup
type: feat
---

## Signalement

- Projet source : devinoo
- Nature : idee
- Reçu le : 2026-10-22

## Description

Dans une file, chaque ticket part de develop avant que la PR du ticket précédent soit mergée par CIWatcher. Les mises à jour de doc par ticket (memory/documentation.json, docs/ARCHITECTURE.md, README.md) touchent les mêmes lignes : dès que la PR N est mergée, la PR N+1, déjà ouverte avec une CI verte, passe en CONFLICTING et CIWatcher ne peut plus la merger. Le rebase de Tessera (git_workspace) fait déjà une union de documentation.json, mais rien ne traite une PR devenue conflictuelle après coup, côté GitHub. Pistes : merge=union pour memory/documentation.json dans .gitattributes des projets, ou CIWatcher qui détecte CONFLICTING, rebase la branche en reprenant l'union, repousse et réattend la CI ; ou bien faire partir le ticket suivant de la branche livrée du précédent.

## Contexte

Devinoo, file c169c10f, 22/10 ~09:25 UTC : PR #124 (ticket-075) CONFLICTING après le merge de #125 (ticket-076) ; conflits dans documentation.json (ids 075/076) et ARCHITECTURE.md (deux paragraphes au même endroit). Résolu à la main par union (6850e49). Constat annexe : le README généré pour 075 annonçait « trois onglets » pour quatre, et des statistiques de « revenus » qui n'existent pas (corrigé 84f6f36) : même symptôme que la doc Haiku de Kadoomi.

## Critères d'acceptation

- [ ] Avant son rebase, la phase 1 de livraison d'un ticket attend que les autres tickets du projet tenus par `CIWatcher` (`en_attente`) soient mergés ou bloqués
- [ ] L'attente est bornée : passé le délai, la livraison part comme avant et ne lève pas
- [ ] Le ticket livré n'est jamais attendu lui-même, et un ticket précédent bloqué n'arrête pas la livraison
- [ ] Rien n'est forcé : aucun push forcé, la tête poussée reste celle que le reviewer a lue (ADR-022, ADR-039)
- [ ] Une ADR au prochain numéro libre décrit la décision et les pistes écartées, et la règle s'écrit sous `## Proposées` de `contraintes.md`

## Ce que ça ne fait pas

- Ne répare pas une PR déjà conflictuelle (poussée à la main, base bougée hors file) : elle reste arrêtée sur « à rebaser » (ticket-452). Voir le ticket de suite.
- Ne change ni le format de `documentation.json` ni la façon dont la doc est écrite par ticket.