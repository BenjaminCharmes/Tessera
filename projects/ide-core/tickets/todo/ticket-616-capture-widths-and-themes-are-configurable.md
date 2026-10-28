---
id: ticket-616
title: "Capture widths and themes are configurable per project"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
created: 2026-10-27
---

# ticket-616 — Largeurs et thèmes de capture configurables

## Objectif
Qu'un projet choisisse les largeurs et les thèmes de ses captures, pour voir
une cassure entre 1024 et 1150 px. Premier ticket de l'ADR-062 ; il ne change
rien pour un projet qui ne déclare rien.

## À faire
- `captures_config.py` : lire `largeurs` (liste d'entiers entre 200 et 3000,
  sans doublon) et `themes` (sous-ensemble de `clair`, `sombre`) dans la section
  `captures`. Absents ou invalides : les valeurs actuelles, 390 et 1440,
  `clair` et `sombre`. `ConfigCaptures` les porte.
- `captures.py` : `noms_attendus`, `_charge` et `MOTIF_FICHIER` lisent la
  configuration au lieu des constantes. Le motif accepte tout entier de
  largeur, pas seulement 390 et 1440 ; la route `GET .../captures/{fichier}`
  garde son refus de tout nom hors forme.
- `scripts/captures.mjs` : une hauteur de viewport pour une largeur absente de
  `HAUTEUR` (900 déjà en repli — ne pas casser).

## Critères d'acceptation
- [ ] Sans `largeurs` ni `themes` dans `agents.json`, `noms_attendus` renvoie les mêmes quatre noms par écran qu'avant
- [ ] Avec `largeurs: [390, 1024, 1440]`, trois largeurs par thème sont attendues et le motif accepte `x-1024-clair.png`
- [ ] Une largeur hors bornes, un doublon ou un thème inconnu retombent sur les valeurs par défaut, sans exception
- [ ] La route de service d'une image refuse toujours `../x.png` et un nom hors motif
- [ ] Un test par fonction publique touchée

## Ce que ça ne fait pas
- Ne lance aucune capture dans un run : c'est ticket-618.
