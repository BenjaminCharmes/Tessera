---
id: ticket-176
title: "Un dépôt personnel sans CI n'a aucun chemin vers le merge automatique"
type: design
status: todo
pr_number: null
priority: high
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-176 — Merger sans CI : décider, ou assumer

## Objectif

Trancher si un pipeline approuvé suffit à merger quand aucune CI ne peut
répondre.

## Contexte

Sept tickets enchaînés sur le banc d'essai, sept approbations en un tour, sept
PR ouvertes automatiquement. Et sept PR **qui attendent un clic**.

Le travail avance : ADR-018 avance la ref de base à chaque approbation, donc
chaque ticket bâtit sur le précédent sans que sa PR soit mergée. Ce qui stagne,
c'est `main`.

`autonomy: merge` existe pour ça, mais ADR-029 l'assortit d'une condition —
*si et seulement si la CI est verte*. Ce dépôt n'a pas de CI utilisable : le
quota Actions des dépôts privés est épuisé, et le runner local est refusé par
la politique de sécurité du poste. Le niveau `merge` ne conclurait donc jamais,
et ADR-030 borne l'attente pour ne pas bloquer la file.

### Ce qu'ADR-029 dit déjà

> Le raisonnement d'ADR-022 — merger, c'est décider qu'un travail est bon —
> tient sur le dépôt d'un client. **Il ne vaut pas sur un dépôt personnel doté
> d'une CI** : y refuser le merge ne protège personne, ça ajoute un clic.

Le cas « dépôt personnel **sans** CI » n'a pas été prévu. Or quatre agents ont
déjà jugé le travail — codeur, sécurité, reviewer, validateur — et ADR-039 fait
échouer fermées les deux portes qui comptent.

## La question

Le verdict du pipeline est-il un signal suffisant quand aucune CI ne peut en
produire un ? Ou l'absence de CI est-elle précisément ce qui rend le clic
humain nécessaire ?

Trois réponses possibles :

1. **Rien ne change** — sans CI, pas de merge automatique. Les PR s'accumulent
   et se mergent par lot. Défendable : ADR-029 pose que l'absence de signal
   n'est pas un signal favorable.
2. **Le projet déclare qu'il n'a pas de CI**, et accepte le merge sur le seul
   verdict du pipeline. La déclaration rend le choix explicite, dans la forme
   d'ADR-021 et ADR-023 : le défaut protège, l'exception s'énonce.
3. **Distinguer « pas de CI » de « CI en attente »** — un dépôt sans aucun
   workflow ne produira jamais de verdict, attendre n'a pas de sens ; un dépôt
   qui en a un et se tait est un vrai *pending*. Ne débloquerait pas ce dépôt,
   qui **a** un workflow que la facturation empêche de tourner.

## Critères d'acceptation

- [ ] La décision est prise et écrite dans un ADR
- [ ] Si elle ouvre le merge sans CI, la déclaration est par projet et son
      absence garde le comportement actuel
- [ ] ADR-029 est amendé ou explicitement confirmé, pas laissé ambigu

## Dépendances

Aucune. La décision appartient à l'utilisateur : c'est son dépôt qui reçoit
les merges.

## Estimation

Une discussion, puis moins d'une journée.

## Risques

Ouvrir le merge sans CI retire la dernière relecture humaine d'une chaîne
entièrement automatique. Sur un dépôt personnel c'est un choix ; le même
réglage recopié sur un dépôt client ne le serait pas.
