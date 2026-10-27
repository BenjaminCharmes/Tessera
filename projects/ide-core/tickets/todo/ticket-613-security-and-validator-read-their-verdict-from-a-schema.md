---
id: ticket-613
title: "Security audit and validator read their verdict from a structured output"
type: feat
status: todo
priority: medium
agent: codeur
created: 2026-10-27
depends_on: [ticket-612]
estimated_days: 1
---

# ticket-613 — Sécurité et validateur sur un schéma

## Objectif
Remplacer `extract_json` par la sortie structurée dans `security_auditor.py` et
`validator.py`, sans rien relâcher de l'échec fermé (ADR-039, ADR-061).

## Schémas (draft-07)
Sécurité — requis : `verdict`, `issues`, `summary` :
- `verdict` : enum `PASS` | `BLOCK`
- `issues[]` : `severity` (enum des clés de `_SEVERITIES`), `type`, `location`,
  `description`, `fix` (chaînes), `introduced` (booléen) ; requis : `severity`,
  `description`, `introduced`
- `summary` : chaîne

Validateur — requis : `criteria`, `feedback` :
- `criteria[]` : `index` (entier), `passed` (booléen), `note` (chaîne) ;
  requis : `index`, `passed`. `criterion` (texte) reste optionnel pour la
  réconciliation tolérante existante.
- `feedback` : chaîne. Pas de champ `verdict` : il se recalcule déjà depuis
  les critères.

## Règles qui restent
- Sécurité : seul `PASS` explicite passe ; `CRITICAL` ou `HIGH` bloque malgré
  `PASS` ; un `introduced` absent vaut vrai. La relance unique du ticket-436
  reste, sur `structured is None`.
- Validateur : un critère absent de la réponse échoue, et le verdict se recalcule.
- `structured is None` → `BLOCK` / `CHANGES_REQUESTED`, avec la cause dans `reason`.
  `extract_json` n'est plus appelé par ces deux services (il reste pour les autres).
- Les prompts `securite.md` et `validateur.md` ne demandent plus de recopier le
  JSON : ils décrivent le fond, le schéma porte la forme.

## Critères d'acceptation
- [ ] Les deux services passent leur schéma à `provider.complete` et lisent `result.structured`, testé avec un double de provider
- [ ] `structured=None` → `BLOCK` pour la sécurité (après la relance) et `CHANGES_REQUESTED` pour le validateur, testé
- [ ] Une faille `CRITICAL` ou `HIGH` avec `verdict: PASS` bloque toujours, testé
- [ ] `introduced` absent est lu vrai, un critère manquant échoue, testés
- [ ] Les tests existants de ces deux services passent, réécrits seulement là où ils fournissaient un texte
- [ ] Un test d'intégration avec le double Ollama (`format` présent dans le corps de la requête) couvre le validateur
- [ ] Les deux prompts sont mis à jour et un test les confronte au schéma (mêmes noms de champs)

## Ce que ça ne fait pas
- Ne touche pas au reviewer : ticket-614.
- Ne change ni les modèles ni les replis déclarés dans `agents.json`.
