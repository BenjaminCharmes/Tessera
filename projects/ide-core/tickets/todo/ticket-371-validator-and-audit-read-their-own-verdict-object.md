---
id: ticket-371
title: "The validator and the security audit read their own verdict object, not the first JSON in the answer"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-07
---

# ticket-371 — Le validateur et l'audit lisent leur propre objet de verdict

## Objectif

Qu'un objet JSON cité dans la réponse d'un agent (un corps de requête tiré
d'un test, un exemple) ne soit jamais pris pour son verdict.

## Contexte

`extract_json` (`backend/src/tessera/utils/json_extract.py`) rend le
**premier** objet JSON valide de la réponse : d'abord dans un bloc
` ```json `, sinon en balayant le texte. Le validateur
(`backend/src/tessera/services/validator.py`) et l'audit sécurité
(`backend/src/tessera/services/security_auditor.py`) s'en servent pour lire
leur verdict.

Le 2026-10-07, le ticket-370 a été refusé deux tours de suite avec
« 5 critère(s) absent(s) de la réponse du validateur » et un retour vide : le
validateur avait bien répondu, mais l'objet retenu n'avait ni `criteria` ni
`feedback`. Les tests de ce ticket envoient des corps
`{"project_id": ".."}` ; le validateur, qui reçoit ces fichiers parce que les
critères les citent (ticket-316), les reprend dans sa réponse.

Côté audit, c'est pire : `parsed.get("verdict", "PASS")` traite un objet sans
`verdict` comme un succès sans faille. Un JSON cité avant le verdict fait
**passer** un audit, à rebours d'ADR-039 (l'audit échoue fermé).

## Solution proposée

1. `extract_json(text, required_key=None)` : avec `required_key`, rendre le
   premier objet qui **contient** cette clé, en cherchant dans les blocs
   ` ```json ` puis dans tout le texte ; `None` si aucun objet ne la porte.
   Sans `required_key`, le comportement actuel est inchangé (les autres
   appelants ne bougent pas).
2. Le validateur appelle `extract_json(raw, required_key="criteria")`.
3. L'audit appelle `extract_json(raw, required_key="verdict")`, et un objet
   sans `verdict` reconnu n'est plus jamais un `PASS` : il rend `BLOCK`, comme
   une réponse illisible.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_json_extract.py` vérifie qu'avec `required_key="criteria"`, une réponse qui contient d'abord un bloc json `{"project_id": ".."}` puis l'objet de verdict rend l'objet de verdict
- [ ] Un test de `backend/tests/test_json_extract.py` vérifie que sans `required_key` le premier objet est toujours rendu
- [ ] Un test de `backend/tests/test_validator.py` vérifie qu'une réponse qui cite un objet JSON avant son verdict voit chacun de ses critères jugé, sans « non jugé par le validateur »
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'une réponse qui cite un objet JSON avant un verdict `BLOCK` rend `BLOCK`
- [ ] Un test de `backend/tests/test_security_auditor.py` vérifie qu'une réponse dont aucun objet ne porte `verdict` rend `BLOCK`, jamais `PASS`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Une réponse d'audit mal formée qui passait par défaut sera désormais bloquée :
c'est le comportement voulu (ADR-039).

## Ce que ça ne fait pas

- Ne change pas les autres appelants d'`extract_json` (planificateur,
  créateurs d'agents et de projets, analyseur).
- Ne conserve pas la réponse brute des agents en base.
