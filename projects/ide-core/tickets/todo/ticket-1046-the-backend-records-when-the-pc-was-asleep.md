---
id: ticket-1046
title: "Le backend enregistre les périodes où le PC était en veille"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-23
---

# ticket-1046 — Les périodes de veille sont connues

## Objectif
Que Tessera sache dire « le PC était en veille de A à B », pour expliquer un
rituel en retard sans que Benjamin ait à deviner.

## Contexte
`rituels_echeances.calculer_echeances` ne connaît que l'heure du PC : un rituel
passé en `en_retard` n'a aucune cause visible. Aucune trace n'existe de la veille.
Le backend ne tourne que PC allumé ; un trou dans un battement régulier est
donc la veille (ou l'arrêt du backend, qu'on ne distingue pas et qu'on dit
sans prétendre plus).

## Solution proposée
- Un battement toutes les 60 s, gardé dans la base (`settings.ide_db_path`,
  table créée par `init_db` de `services/noyau/database.py`), qui retient le
  dernier instant. La base, déjà isolée par `conftest.py`, survit au
  redémarrage : le premier battement après un arrêt voit l'écart.
- Au battement suivant, un écart de plus de 10 minutes s'enregistre comme
  « interruption » (début = dernier battement, fin = maintenant) ; on ne garde
  que les 30 dernières.
- Les instants sont pris sur la même horloge que les rituels : `datetime.now()`
  local et naïf, comme `derniere` (`routers/rituels.py`). Le front les compare
  tels quels à `derniere` (ticket-1047) : une heure UTC décalerait le test
  d'une heure.
- `GET /api/v1/rituels/interruptions` rend, sous le jeton de session habituel,
  un `response_model` de forme `{"interruptions": [{"debut": "…", "fin": "…"}]}`,
  la plus récente en premier. Ce contrat est celui que lit ticket-1047.
- La route change le schéma : régénérer `docs/openapi.json` (`make openapi`),
  et ranger `"GET /api/v1/rituels/interruptions"` dans `HORS_PERIMETRE` de
  `frontend/src/test/contrat/perimetre.ts`, comme `GET /api/v1/rituels`, sans
  quoi `contrat.test.ts` échoue.
- Un module de `services/projets/` (le domaine des rituels, ADR-076), un test
  par fonction publique.

## Critères d'acceptation
- [ ] Un test montre qu'un écart de 11 minutes entre deux battements crée une interruption de début = battement précédent et fin = battement courant, et qu'un écart de 5 minutes n'en crée pas.
- [ ] Un test montre que la 31e interruption fait sortir la plus ancienne.
- [ ] Un test de `routers/rituels.py` montre que `GET /api/v1/rituels/interruptions` rend 401 sans jeton et, avec, un corps `{"interruptions": [...]}` dont chaque entrée a `debut` et `fin`, la plus récente en premier.
- [ ] Le battement démarre dans le `lifespan` de `main.py` et s'arrête après son `yield`.
- [ ] Un test montre qu'un battement dont l'écriture échoue journalise l'échec et ne lève pas.
- [ ] `docs/openapi.json` contient la route, et `frontend/src/test/contrat/perimetre.ts` la range dans `HORS_PERIMETRE`.
- [ ] `uv run mypy src/` passe sans erreur sur les fichiers ajoutés.

## Dépendances
Aucune. Prépare ticket-1047.

## Estimation
Un jour.

## Risques
Un redémarrage du backend compte comme une interruption : la formulation côté
interface (ticket-1047) dit « Tessera n'a pas tourné », pas « veille ».
