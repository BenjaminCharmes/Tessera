---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 1
id: ticket-1033
priority: medium
status: done
title: A ritual can be daily
type: feat
---

# ticket-1033 — Un rituel peut être quotidien

## Signalement

- Projet source : carriere (20/11)
- Besoin : un rituel « journal du jour », chaque soir, à côté du point hebdo.
  Le format des rituels ne connaît pas de rythme quotidien.

## Contexte

`backend/src/tessera/services/projets/rituels_echeances.py` accepte trois
rythmes : `Hebdo`, `Mensuel`, `Unique` (union discriminée sur `type`). Un
`type: quotidien` dans `rituels.md` rend aujourd'hui une erreur de lecture
(`test_unknown_rhythm_type_gives_error`). Côté interface,
`frontend/src/lib/apiRituels.ts` (`RythmeRituel`) et
`frontend/src/components/RituelsView/format.ts` (`libelleDuRythme`) ne
connaissent que ces trois types : un type inconnu tomberait dans la branche
`Du … au …`.

## Solution proposée

**Backend** — dans `rituels_echeances.py` :

- un modèle `Quotidien` : `type: Literal["quotidien"]`, `heure: time`,
  `jours: Literal["tous", "ouvres"] = "tous"` ; il entre dans `Rythme` et dans
  les signatures de `_bornes`, `_limite` et `calculer_echeances` ;
- `_bornes` : la dernière échéance est le dernier jour retenu dont l'heure est
  passée, la prochaine le jour retenu suivant. Avec `jours: ouvres`, samedi et
  dimanche ne sont jamais retenus (un lundi à 10:00 pour un rituel de 18:00,
  la dernière est le vendredi 18:00, la prochaine le lundi 18:00) ;
- `_limite` : pas de limite pour un quotidien.

**Frontend** :

- `RythmeRituel` gagne `{ type: "quotidien"; heure: string; jours: "tous" |
  "ouvres" }` ;
- `libelleDuRythme` rend « Chaque jour à 18:00 » ou « Chaque jour ouvré à
  18:00 ».

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_rituels.py` : un `rituels.md` avec
      `rythme: { type: quotidien, heure: "18:00" }` est lu sans erreur.
- [ ] Un test : rythme quotidien à 18:00, `jours` par défaut — un mercredi à
      10:00, la dernière échéance est le mardi 18:00 et la prochaine le
      mercredi 18:00 ; un mercredi à 19:00, la dernière est le mercredi 18:00
      et la prochaine le jeudi 18:00.
- [ ] Un test : avec `jours: ouvres`, un lundi à 10:00 la dernière échéance
      est le vendredi 18:00 et la prochaine le lundi 18:00 ; un samedi à
      12:00, la dernière est le vendredi 18:00 et la prochaine le lundi 18:00.
- [ ] Un test : un quotidien jamais fait est `en_retard`, fait après sa
      dernière échéance il est `fait`, et `depasse` est toujours faux.
- [ ] Un test frontend de `libelleDuRythme` (fichier
      `frontend/src/components/RituelsView/format.test.ts`) rend « Chaque jour
      à 18:00 » et « Chaque jour ouvré à 18:00 ».
- [ ] `pytest`, `mypy`, `tsc`, `eslint` et `vitest` passent.

## Ce que ça ne fait pas

- N'ajoute aucun rituel à `rituels.md` : le rituel « journal du jour » s'y
  écrit à la main quand le projet qui le demande est prêt.
- Ne connaît pas les jours fériés.
- Ne change ni la synchronisation des rituels ni les routes.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`test_unknown_rhythm_type_gives_error` doit garder un type vraiment inconnu :
vérifier qu'il n'utilise pas `quotidien`.