---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.25
id: ticket-475
pr_number: null
priority: medium
status: done
title: A dotted identifier in a criterion is not taken for a cited file
type: fix
---

# ticket-475 — Un identifiant pointé n'est pas un fichier cité

## Objectif

`BRAND.name`, `settings.github_token` ou `user.email` entre backticks dans un
critère ne sont plus cherchés comme fichiers ni rapportés « absents ».

## Contexte

make-your-call, 16/10, ticket-017 : « validateur : fichiers cités joints :
CLAUDE.md, memory/decisions.md ; absents : BRAND.name, BRAND.domain ».
`extract_file_refs` dans
`backend/src/tessera/services/validator_cited_files.py` retient tout texte
entre backticks qui finit par une extension de 1 à 6 lettres : `.name`,
`.domain` passent.

## Solution proposée

Un texte est retenu comme fichier s'il contient un `/`, ou si son extension
appartient à une liste d'extensions de fichiers connues (code, config,
documents, images : `py ts tsx js jsx mjs json md yml yaml toml css html sql
prisma env txt png svg …`). Sinon il est ignoré.

## Critères d'acceptation

- [ ] Un test vérifie que `BRAND.name` et `settings.github_token` ne sont
      pas extraits
- [ ] Un test vérifie que `brand.ts`, `src/lib/brand.ts` et
      `prisma/schema.prisma` le sont toujours
- [ ] Un test vérifie que `docs/notes.unknownext` (avec un `/`) l'est