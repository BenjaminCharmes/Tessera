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
- Un battement toutes les 60 s dans une table `battements` ou un fichier
  d'état sous `IDE_STATE_DIR`, qui garde le dernier instant.
- Au battement suivant, un écart de plus de 10 minutes s'enregistre comme
  « interruption » (début = dernier battement, fin = maintenant) ; on ne garde
  que les 30 dernières.
- `GET /api/v1/rituels/interruptions` rend la liste, sous le jeton de session
  habituel.
- Un module de `services/` dans son domaine (ADR-076), un test par fonction publique.

## Critères d'acceptation
- [ ] Un test montre qu'un écart de 11 minutes entre deux battements crée une interruption, et qu'un écart de 5 minutes n'en crée pas.
- [ ] Un test montre que la 31e interruption fait sortir la plus ancienne.
- [ ] Un test de `routers/rituels.py` montre que `GET /api/v1/rituels/interruptions` rend 401 sans jeton et la liste avec.
- [ ] Le battement démarre avec le backend dans `main.py` et s'arrête à son arrêt, sans bloquer le démarrage si l'écriture échoue (échec journalisé).
- [ ] `uv run mypy src/` passe sans erreur sur les fichiers ajoutés.

## Dépendances
Aucune. Prépare ticket-1047.

## Estimation
Un jour.

## Risques
Un redémarrage du backend compte comme une interruption : la formulation côté
interface (ticket-1047) dit « Tessera n'a pas tourné », pas « veille ».
