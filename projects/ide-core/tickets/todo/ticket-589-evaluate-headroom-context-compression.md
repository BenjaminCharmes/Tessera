---
id: ticket-589
title: "Design: evaluate headroom to compress the context sent to agents"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: []
estimated_days: 1
created: 2026-10-26
plan: true
---

# ticket-589 — Conception : compresser le contexte des agents avec headroom

## Objectif
Décider si Tessera compresse ce qu'il envoie aux agents (sorties de tests,
logs, diffs) avec headroom, et par quel point d'entrée.

## Contexte
Veille Vigie du 26/10 (édition 2026-W44, « Peut servir à Tessera ») :
headroom (https://github.com/headroomlabs-ai/headroom) réduit les tokens des
sorties d'outils, des logs et des extraits RAG avant l'appel au modèle. Il
existe en bibliothèque Python, en proxy et en serveur MCP, avec un support
Anthropic, et annonce 20 à 95 % de tokens en moins selon le type de données.
Ce sont les chiffres du projet, pas les nôtres.

Le quota hebdomadaire est le goulot de Tessera : il a coupé les files les
16, 17, 18 et 24/10. Le testeur, le reviewer et le validateur reçoivent de
longues sorties (`scripts/verifier.py`, diffs).

La contrainte : les services passent par `LLMProvider` (ADR-017), et le
provider Claude s'appuie sur le CLI embarqué par l'Agent SDK. Une
bibliothèque ne s'y branche pas telle quelle : il faut soit compresser avant
l'appel, dans le texte du prompt, soit faire passer le CLI par le proxy, soit
passer par MCP, ce qui ne couvre que les sorties d'outils.

## Solution proposée
- Mesurer sur deux ou trois runs réels d'ide-core les tokens d'entrée par
  rôle, puis ce que headroom en retire sur ces mêmes entrées, hors ligne.
- Comparer les trois points d'entrée : coût, risque de perte d'information
  pour un verdict (une ligne d'erreur pytest tronquée fait un faux
  APPROVED), compatibilité avec l'échec fermé (ADR-039).
- Recommander d'adopter, de reporter ou d'écarter.

## Critères d'acceptation
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le point d'entrée retenu, ou pourquoi headroom est écarté
- [ ] Le livrable chiffre, rôle par rôle, les tokens d'entrée mesurés et ceux obtenus après compression, sur au moins deux runs réels
- [ ] Le livrable liste les tickets d'implémentation qui en découlent, chacun avec ses critères vérifiables

## Ce que ça ne fait pas
- N'implémente rien : ticket de conception.
- N'ajoute aucune dépendance au backend.
