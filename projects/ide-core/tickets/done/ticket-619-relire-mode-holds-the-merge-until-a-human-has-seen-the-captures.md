---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-618
id: ticket-619
priority: medium
status: done
title: 'Relire mode: a pull request with visual checks is never merged alone'
type: feat
---

# ticket-619 — Mode `relire` : la PR attend un humain

## Objectif
Sur un projet en `autonomy: merge`, un `controle_visuel: "relire"` qui s'est
déclenché ouvre la PR sans la remettre au `CIWatcher`. Sans quoi, les captures
d'un projet qui merge seul ne seraient vues par personne avant le merge.

## À faire
- Réutiliser le mécanisme d'ADR-033 (« une PR ne se merge jamais seule ») : la
  PR s'ouvre, le ticket reste `done`, la raison est écrite dans le journal.
- Un échec de l'étape de capture vaut le même arrêt (ADR-039 : une porte qui
  n'a pas pu voir ne laisse pas passer).
- En `joindre`, rien ne change.

## Critères d'acceptation
- [ ] Mode `relire`, étape déclenchée, captures prises : PR ouverte, `CIWatcher` n'en reçoit pas le merge
- [ ] Mode `relire`, étape déclenchée, captures échouées : même résultat, cause au journal
- [ ] Mode `relire`, diff sans fichier d'interface : livraison inchangée, merge normal
- [ ] Mode `joindre` et projet sans déclaration : livraison inchangée
- [ ] Un run non approuvé ne se livre toujours pas (ADR-030)

## Conséquence à connaître
`depends_on` attend le merge (ADR-051, ADR-060) : un ticket qui dépend d'un
ticket en `relire` reste bloqué tant qu'un humain n'a pas relu et mergé la PR.
Un projet en `relire` perd donc le merge automatique sur chaque diff d'interface.

## Ce que ça ne fait pas
- Ne rend aucun verdict sur les images.