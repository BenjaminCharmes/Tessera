---
agent: codeur
created: 2026-11-23
depends_on: []
estimated_days: 0.5
id: ticket-1045
pr_number: null
priority: medium
status: done
title: Chaque rituel de rituels.md tombe en semaine, pendant les heures où le PC est
  allumé ; le journal du jour disparaît
type: chore
---

# ticket-1045 — Rituels en semaine, en journée

## Objectif
Qu'aucun rituel hebdomadaire ne tombe un soir, une nuit ou un week-end : le PC
est alors éteint ou en veille, et l'échéance n'est vue qu'au réveil. Un rituel
mensuel garde son jour du mois ; s'il tombe un samedi, il est vu le lundi, et
ticket-1047 dira pourquoi.

## Contexte
Le PC n'est allumé que la semaine en journée, jusqu'au homelab. Dernière
occurrence : veille le 22/11 à 17:26, réveil le 23/11 à 09:12 ; le tour Vigie
de dimanche 23 h (`RUN_CRON=0 23 * * 0`) est donc parti en rattrapage au réveil,
au moment même où `lecture-veille` (lundi 09:00) et `radar-hebdo` (lundi 09:30)
s'affichent : la veille se lit avant que l'édition existe.
Le cron de Vigie ne bouge pas : l'édition est rangée dans la semaine qu'elle
couvre (ADR-029), le déplacer changerait cette semaine.

## Solution proposée
Ne modifier que `rituels.md` (le fichier, pas le code) :
- `lecture-veille` : lundi 10:30 ; `radar-hebdo` : lundi 11:00 (laisse au tour
  de rattrapage le temps de finir).
- `point-revenus` : lundi 18:30 → lundi 14:00.
- `journal-du-jour` : supprimé (décision de Benjamin le 23/11 : le point hebdo
  suffit). Son état « fait » en base locale peut rester, il est ignoré.
- `portfolio-hebdo` : vendredi 17:00 → vendredi 14:00.
Les autres rituels (jour du mois ou vendredi 16:00, 09:00-10:00) restent.
Ajouter à la section « Écrire un rituel » une phrase : une heure se choisit
quand le PC est allumé, en semaine.
Corriger l'introduction du fichier, qui dit encore que Tessera « affiche un
bandeau sur toutes ses vues » : il n'y en a pas (écarté au ticket-903), c'est
une pastille sur l'onglet Rituels et une entrée de cloche.

## Critères d'acceptation
- [ ] `rituels.md` donne à `lecture-veille` l'heure `"10:30"` et à `radar-hebdo` l'heure `"11:00"`, toujours le lundi.
- [ ] `rituels.md` donne à `point-revenus` l'heure `"14:00"` et à `portfolio-hebdo` l'heure `"14:00"`, sans changer leur jour.
- [ ] `rituels.md` ne contient plus d'entrée d'`id` `journal-du-jour`, et `point-hebdo-travail` y reste avec son détail inchangé.
- [ ] Un test lit `rituels.md` du dépôt avec `lire_definitions` et vérifie qu'aucun rythme `hebdo` ou `quotidien` n'a une heure avant 08:00 ou après 17:59, ni un jour `samedi` ou `dimanche`.
- [ ] `rituels.md` dit, dans « Écrire un rituel », qu'une heure se choisit en semaine pendant que le PC est allumé.
- [ ] `rituels.md` ne contient plus le mot « bandeau ».

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
L'état « fait » reste rattaché à l'`id` : aucun rituel ne perd son historique.
Ce ticket ne retire pas `passe-black-friday-2026` : elle court jusqu'au 27/11.