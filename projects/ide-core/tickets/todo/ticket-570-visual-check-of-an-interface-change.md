---
id: ticket-570
title: "Design of an opt-in visual check: screenshots at three widths for a run that changes an interface"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: []
estimated_days: 1
created: 2026-10-23
plan: true
---

# ticket-570 — Conception d'un contrôle visuel optionnel

## Objectif
Décider comment un run qui modifie une interface peut être vu, et pas
seulement lu, avant le merge — sans alourdir les projets qui n'en ont pas
besoin.

## Contexte
Le 23/10, Kadoomi a relu à l'œil sa release : avec sept occasions, l'en-tête
public chevauchait le logo entre 1024 et ~1150 px. Ni le reviewer ni le
validateur ne l'avaient vu : ils lisent un diff. Le même jour, une capture
Playwright a validé les cartes de projet du ticket-557 avant leur PR. Le
pipeline ne fait aucune capture.

## À trancher par la conception
- **Opt-in par projet** dans `agents.json` (aucun projet ne le subit sans le
  déclarer) : quelles pages, comment lancer l'app (services déclarés,
  ADR-042), quelles largeurs (par exemple 390, 1024, 1440).
- Quand : seulement si le diff touche des fichiers d'interface.
- Qui regarde : le validateur reçoit les captures (modèle qui lit l'image),
  ou elles sont seulement jointes à la PR pour l'humain.
- Coût : temps ajouté par run, quota, échec d'un serveur qui ne démarre pas
  (la porte échoue-t-elle fermée ou ouverte ?).
- Où vivent les captures : hors du dépôt (ADR-021).

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le contrôle retenu, ou pourquoi il est écarté
- [ ] Le livrable chiffre le temps ajouté à un run sur Kadoomi
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables, et aucun ne s'applique à un projet qui ne l'a pas déclaré

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.
