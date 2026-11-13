---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-968
pr_number: null
priority: medium
status: done
title: Every project repository carries the forbidden-terms pre-push hook
type: fix
---

# ticket-968 — Chaque dépôt de projet porte le hook pre-push des termes interdits

## Objectif

Qu'une retouche poussée à la main depuis le dépôt d'un projet passe par la
porte `pre-push` des termes interdits (ADR-050), comme dans Tessera.

## Contexte

Relevé de cohérence entre projets (13/11). `make install-hooks` copie
`scripts/hooks/pre-push` dans le seul `.git/hooks` de Tessera. Aucun des
dépôts de `projects/` n'a de hook, et sept n'ont pas de CI. Le pipeline
contrôle ses propres push, mais les retouches à la main des sessions de
projet ne passent par aucune des trois portes. Le hook lit la liste par le
backend (ADR-073) depuis le dépôt Tessera.

## Solution proposée

1. Un hook de projet minimal, écrit dans `.git/hooks/pre-push` de chaque
   dépôt de projet, qui appelle `scripts/hooks/pre-push` de Tessera par son
   chemin absolu, avec les mêmes arguments et la même entrée standard.
2. Il est posé à l'import, à la création d'un projet et par une commande
   `scripts/tessera.ps1 hooks` qui le pose sur tous les projets existants et
   dit ce qu'elle a fait.
3. Un projet `"confidentiality": "professional"` n'en reçoit pas
   (ADR-048) ; un hook `pre-push` déjà présent et différent n'est jamais
   écrasé : la commande le signale.

## Critères d'acceptation

- [ ] Un test (`tmp_path`, dépôt git réel) : après l'installation, un push
      vers un dépôt nu local d'un commit contenant un terme interdit (liste
      de test) est refusé ; sans terme interdit, il passe.
- [ ] Un test : un projet `professional` ne reçoit pas de hook.
- [ ] Un test : un `pre-push` existant et différent n'est pas modifié, et le
      retour le nomme.
- [ ] Un test : l'import d'un projet pose le hook.

## Ce que ça ne fait pas

- N'ajoute pas de CI aux projets qui n'en ont pas.
- Ne touche pas au hook de Tessera lui-même.