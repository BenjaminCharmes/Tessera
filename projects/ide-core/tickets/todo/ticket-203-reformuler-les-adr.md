---
id: ticket-203
title: "Reformuler les ADR qui racontent un usage réel au lieu d'une règle"
type: docs
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-203 — Reformuler les ADR qui racontent un usage réel

## Objectif

Réécrire les « Raison » et « Alternative rejetée » des ADR qui décrivent la
situation réelle de l'utilisateur, pour qu'ils justifient la règle par un cas
**hypothétique** — sans changer aucune règle.

## Contexte

Aucun nom d'employeur, de client ni de projet de travail n'est versionné.
Mais plusieurs ADR racontent un usage réel : le nombre de dépôts clients
posés dans `projects/`, l'accident qui a fait naître une règle, le signalement
d'un service de sécurité. Un agent n'a besoin que du mécanisme pour appliquer
la règle ; l'anecdote ne lui apprend rien et coûte des tokens dans chaque
appel (`decisions.md` part dans chacun, jusqu'à dix-huit par ticket).

ADR concernés, par ligne relevée : ADR-021, 022, 023, 024, 028, 029, 031, 036,
043. Le cas le plus net est ADR-043, dont la « Raison » décrit l'incident
d'origine.

## Solution proposée

- « dépôt client » → « dépôt tiers » ou « dépôt qu'on ne possède pas » quand
  la phrase décrit une situation ; le mot reste quand il nomme un **usage
  prévu** du produit.
- Les chiffres et les récits d'incident (combien de dépôts, combien de
  commits, qui a signalé quoi) deviennent un cas générique : « un dépôt
  personnel rendu public avec une adresse de travail dans ses métadonnées ».
- `Décision`, `Portée` et `Conséquence assumée` ne changent pas de sens. Si
  une formulation de décision doit bouger, le justifier dans la PR.
- Tenir le budget d'ADR-034 (skill `write-adr`) : la reformulation doit
  raccourcir, jamais allonger.

## Critères d'acceptation

- [ ] Aucun ADR ne donne de chiffre ni de récit décrivant l'installation ou
      l'historique réel de l'utilisateur (nombre de dépôts, incident, service
      qui a signalé)
- [ ] Le champ `Décision` de chaque ADR touché garde le même sens — vérifiable
      en relisant le diff ligne à ligne
- [ ] `decisions.md` est plus court après qu'avant
- [ ] `test_consignes_coherentes.py` passe
- [ ] Seul `projects/ide-core/memory/decisions.md` est modifié

## Dépendances

Aucune.

## Estimation

Une demi-journée à un jour.

## Ce que ça ne fait pas

- **L'historique git garde l'ancien texte.** Ce ticket suffit pour un dépôt
  privé. Rendre Tessera public demanderait en plus l'audit des tickets
  `done/` et des plans `docs/`, et un dépôt à l'historique neuf : un commit
  réécrit reste joignable par son SHA sur GitHub.
- Les tickets `done/` ne sont pas touchés : ils ne partent pas dans le prompt.

## Risques

Une reformulation qui généralise trop perd la raison de la règle, et une règle
sans raison se contourne. Garder le **mécanisme** du problème, n'enlever que
son **origine**.
