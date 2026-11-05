---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-830
pr_number: null
priority: medium
status: done
title: decisions.md keeps only the ADRs that still ground a rule, the rest go to the
  archive
type: chore
---

# ticket-830 — decisions.md ne garde que les ADR qui fondent encore une règle

## Objectif

`decisions.md` ne porte que des décisions vivantes, et une ADR remplacée le dit ; le fichier ne
regrossit pas sans que rien ne le signale.

## Contexte

Benjamin, le 05/11 : « on est déjà à 75 ADR, on va finir par approcher des 100 ». Relevé le même
jour : `decisions.md` fait 65 Ko et porte 74 ADR, dont 58 sont citées par `contraintes.md`.
Seize ne le sont pas (ADR-001 à 005, 011, 015, 032, 034, 035, 036, 052, 054, 060, 063, 066).
Aucune ADR n'est marquée comme remplacée, alors que plusieurs ont été reprises par une ADR
postérieure. `decisions-archive.md` existe (une seule ADR) et `test_consignes_coherentes.py`
vérifie déjà que toute ADR citée existe encore, dans l'un ou l'autre fichier
(`test_tout_adr_cite_existe_encore`), et que la numérotation lit les deux fichiers
(`backend/src/tessera/services/numerotation.py`).

## Solution proposée

- Pour chaque ADR de `decisions.md` qu'une ADR postérieure remplace, ajouter la ligne
  `**Remplacée par** : ADR-0xx` et la déplacer dans `decisions-archive.md`.
- Déplacer dans l'archive toute ADR qui n'est citée ni par `projects/ide-core/memory/contraintes.md`,
  ni par `CLAUDE.md` ni par `projects/ide-core/CLAUDE.md`. Une ADR encore citée par un de ces
  fichiers reste. Les numéros ne bougent pas ; un commentaire de code qui cite une ADR archivée
  reste valable (l'archive se lit, `test_tout_adr_cite_existe_encore` le garantit).
- Un test refuse dans `decisions.md` une ADR qui n'est citée par aucun de ces trois fichiers :
  elle doit partir en archive.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_consignes_coherentes.py` vérifie que chaque ADR de
      `projects/ide-core/memory/decisions.md` est citée par `contraintes.md`, `CLAUDE.md` ou
      `projects/ide-core/CLAUDE.md`, et nomme celles qui ne le sont pas
- [ ] `projects/ide-core/memory/decisions-archive.md` contient les ADR déplacées, avec leur numéro
      d'origine, et une ADR remplacée y porte une ligne `**Remplacée par**`
- [ ] `test_tout_adr_cite_existe_encore` et `test_aucun_adr_ne_depasse_le_budget` passent toujours
- [ ] Le diff ne modifie que `projects/ide-core/memory/decisions.md`,
      `projects/ide-core/memory/decisions-archive.md` et `backend/tests/test_consignes_coherentes.py`
      (et le fichier de ce ticket)

## Ce que ça ne fait pas

`contraintes.md` n'est pas modifié. Aucune règle en vigueur ne change : seul le journal est rangé.