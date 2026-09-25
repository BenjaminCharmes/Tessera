---
id: ticket-168
title: "La règle de langue n'existe qu'à moitié, et la pratique a dérivé"
type: docs
status: done
pr_number: 19
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-168 — Fixer la langue avant de renommer quoi que ce soit

## Objectif

Qu'une règle de langue existe, complète, avant tout renommage.

## Contexte

Le dépôt est destiné à devenir public. Un identifiant français y arrête un
contributeur à la première lecture.

La règle existait à moitié : `CLAUDE.md` impose l'anglais aux **commits** et
aux **docstrings**, et se tait sur les identifiants, les noms de tests et les
pull requests. La pratique a dérivé en conséquence — les titres et corps de PR
de cette semaine sont en français, et des docstrings écrites aujourd'hui aussi.

Mesuré avant de décider :

| | |
|---|---|
| modules à nom français | 3 |
| fonctions et classes | ~15 |
| noms de tests backend | 362 sur 1193 |
| libellés de tests frontend | 142 |
| ADR · tickets · prompts | 42 · 161 · 14 |

Le **code** est donc peu francisé ; le gros du français est de la prose.

## Ce que ce ticket ne fait pas

**Il ne renomme rien.** Un renommage de cinq cents noms sans CI se paierait en
silence — les minutes GitHub sont épuisées et le runner local est bloqué par la
politique du poste. Le renommage attend son retour ; ce ticket pose la règle
pour que la dérive s'arrête aujourd'hui.

Il ne traduit pas non plus les ADR ni les prompts : ils partent dans **chaque**
appel d'agent. Les traduire changerait le comportement du produit, pas sa
lisibilité — et un contributeur lit du code, pas un journal de décisions.

## Solution proposée

1. ADR-044 : identifiants, docstrings, noms de tests, commits et titres de PR
   en anglais ; commentaires, ADR, tickets et prompts en français.
2. `CLAUDE.md` **renvoie** à l'ADR au lieu d'en porter une seconde version
   (ADR-034). Ce ticket autorise explicitement cette modification (règle 5).
3. `_CONTRAINTES` de `test_adr_pertinents.py` enregistre ADR-044 — c'est une
   contrainte de comportement, elle ne doit jamais porter de portée.

## Critères d'acceptation

- [ ] ADR-044 existe, sans `**Portée**`, et tient dans le budget
- [ ] `"ADR-044"` figure dans `_CONTRAINTES`
- [ ] `CLAUDE.md` renvoie à ADR-044 et ne redécrit pas la règle
- [ ] `CLAUDE.md` mentionne les titres de PR, qui manquaient
- [ ] `uv run pytest` passe

## Dépendances

Aucune. Le renommage effectif dépendra du retour de la CI.

## Estimation

Moins d'une journée.

## Risques

Une règle posée et non appliquée est une dette visible. C'est assumé : la
poser maintenant arrête la dérive, l'appliquer sans filet la remplacerait par
une panne silencieuse.
