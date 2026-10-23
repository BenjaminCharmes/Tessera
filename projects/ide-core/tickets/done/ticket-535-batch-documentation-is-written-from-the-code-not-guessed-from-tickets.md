---
agent: architect
created: 2026-10-22
depends_on:
- ticket-534
estimated_days: 1
id: ticket-535
plan: true
pr_number: null
priority: high
status: done
title: Batch documentation is written from the delivered code, not guessed from tickets
type: design
---

# ticket-535 — La doc par lot s'écrit depuis le code livré

## Objectif
Que la documentation générée par le pipeline ne contienne plus de faits
inventés.

## Contexte
Le 22/10, Kadoomi et Devinoo ont relu la doc par lot de chaque run :
- Kadoomi, lot 077-090 : groupes attribués à ADR-019 et au modèle WishList au
  lieu d'ADR-018 / GroupEvent, migration 0021 au lieu de 0012, 10 Mo et AVIF au
  lieu de 5 Mo et GIF, e-mail de confirmation inexistant, délais de rappel
  inventés ; lot 087 : thème sombre « par défaut », « les réservations
  notifient le groupe » (faux, et sensible pour le secret des réservations).
  Lots jetés en entier.
- Devinoo : « trois onglets » pour quatre, statistiques de « revenus »
  inexistantes, cinq erreurs dans « Gérer ton compte » ; le ticket 078
  (en-têtes de sécurité) a réécrit 94 lignes de guide sans rapport.

Cause : `_brief` de `services/documentation.py` ne donne aux agents que le
**texte des tickets** et la doc actuelle, jamais le code. Un ticket dit
l'intention, pas les noms, les chiffres ni les libellés : l'agent (Haiku sur la
plupart des projets) les devine. Le lot va jusqu'à 10 tickets (`_PLAFOND`), et
inclut les tickets faits à la main.

## À trancher par la conception
- Ce que l'agent reçoit en plus : le diff livré du lot, borné ; ou les
  fichiers que le diff touche ; ou un outil de lecture en lecture seule.
- Taille du lot (`_PLAFOND`) et sort des tickets faits à la main.
- Modèle par défaut des rôles de doc (Sonnet plutôt que Haiku ?), qui reste
  déclaré par projet dans `agents.json`.
- Une règle de périmètre : ne réécrire que les sections liées aux tickets du
  lot (le cas du 078).
- Les conflits de doc entre les PR d'une même file (ticket-533) : la conception
  dit si elle les règle ou les laisse à 533.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit ce que reçoivent les agents de documentation et pourquoi
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables
- [ ] Le livrable cite au moins trois des erreurs relevées le 22/10 et dit, pour chacune, ce qui l'aurait empêchée

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.