---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.25
id: ticket-376
pr_number: null
priority: critical
status: done
title: An agent's JSON answer is read even when a string holds an unescaped backslash
type: fix
---

# ticket-376 — Une réponse JSON se lit même avec une barre oblique inverse non échappée

## Objectif

Qu'un verdict d'agent ne soit plus perdu parce qu'une de ses chaînes contient
un chemin Windows ou une séquence comme `..\x`.

## Contexte

`extract_json` (`backend/src/tessera/utils/json_extract.py`) décode les
objets avec `json.JSONDecoder.raw_decode`, qui refuse une chaîne contenant une
barre oblique inverse non suivie d'un échappement JSON valide (`\x`, `\p`,
`\.`…). L'objet entier devient alors illisible.

Constaté le 2026-10-07 sur le ticket-370 (validation des `project_id`) : la
réponse de l'audit sécurité commençait par
```json { "issues": [], "verdict": "PASS", "summary": "… path traversal …
et son résumé citait un chemin en `..\…`. L'objet était invalide, donc
illisible ; depuis le ticket-371, un audit illisible bloque (ADR-039), et le
run s'est arrêté alors que l'audit avait conclu `PASS`. Avant le ticket-371,
le même cas retombait sur un objet imbriqué valide sans `verdict` et passait
pour un `PASS` par défaut.

Tout ticket qui touche à des chemins Windows ou à des expressions régulières
expose les agents à ce cas.

## Solution proposée

Quand le décodage d'un objet échoue, réessayer une fois après avoir doublé
chaque barre oblique inverse qui n'introduit pas un échappement JSON valide
(`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, `\uXXXX`). Un JSON valide est
décodé exactement comme aujourd'hui ; un JSON cassé pour une autre raison
reste illisible.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_json_extract.py` vérifie que `extract_json('{"verdict": "PASS", "summary": "refuse ..\\x"}', required_key="verdict")` rend un objet dont `verdict` vaut `PASS`
- [ ] Un test de `backend/tests/test_json_extract.py` vérifie qu'un objet valide contenant un échappement de saut de ligne et un échappement unicode est décodé à l'identique, sans doublement
- [ ] Un test de `backend/tests/test_json_extract.py` vérifie qu'un objet cassé pour une autre raison (accolade manquante) rend toujours `None`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'une réponse ```json dont le résumé contient `..\x` et dont le verdict est `PASS` rend `PASS`

## Dépendances

Aucune.

## Estimation

0,25 jour.

## Risques

Une barre oblique inverse doublée change le texte rendu du résumé (un `\`
apparent de plus) : sans effet sur le verdict.

## Ce que ça ne fait pas

- Ne change pas la règle d'échec fermé : une réponse vraiment illisible
  bloque toujours.