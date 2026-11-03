---
id: ticket-765
title: "The route contract test checks field types and cannot be bypassed by vi.mock"
type: test
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-765 — Le test de contrat vérifie les types et ne se contourne plus par `vi.mock`

## Objectif

Le test de contrat du ticket-684 vérifie ce qu'il annonce.

## Contexte

Audit du 30/10 (relecture du 03/11), `frontend/src/test/contrat/`.
- `installerLeGarde` (`garde.ts`) n'enveloppe que `vi.spyOn` : `BranchCleanup.test.tsx` et
  `ProjetCarte.test.tsx` posent leurs réponses par `vi.mock("../../lib/api")`, hors garde.
- La confrontation (`contrat.test.ts`) ne compare que les noms de champs : `ServiceActif.sortie?`
  optionnel côté TS alors que `ServiceEtat` l'exige passe.
- `fs.writeFile` envoie `POST /fs/write` (le backend expose `PUT`) et `listDir` annonce
  `string[]` (la route rend des `DirEntry[]`) : deux fonctions jamais appelées.

## Critères d'acceptation

- [ ] Un test vérifie qu'un champ requis par le schéma OpenAPI mais optionnel dans le type TS
      fait échouer la confrontation
- [ ] Un test vérifie qu'une réponse posée par `vi.mocked(api.git.cleanupPlan).mockResolvedValue(...)`
      passe par le garde (ou que `vi.mock` du module api lève sur le périmètre)
- [ ] `ServiceActif` porte `sortie` et `arrete_a_la_main` comme le schéma
- [ ] Le diff supprime `fs.writeFile` et `fs.listDir` du client
