---
agent: codeur
created: 2026-10-27
depends_on:
- ticket-596
estimated_days: 0.25
id: ticket-601
pr_number: null
priority: medium
status: done
title: A bubble above the working agent says which tool it is using
type: feat
---

# ticket-601 — La bulle d'action de l'agent au travail

## Objectif
Idée 4 du « Bureau vivant » (`design/maquette/Bureau-vivant.dc.html`, bulle
flottante au-dessus du poste occupé), validée le 27/10.

## Contexte
Chaque appel d'outil émet `agent_tool_use` avec `data.tool` et `data.input`
(`backend/src/tessera/services/pipeline_stages.py`). Exemple réel :
`{"tool": "Read", "input": {"file_path": "C:\\…\\conflits.py"}}`. Le
`StreamState` ne garde aujourd'hui qu'un compteur (`outils`).

## Ce que dit la maquette
Au-dessus du poste occupé, une bulle d'une ligne : « lit conflits.py »,
« édite Piece.tsx », « lance pytest », « cherche "santeAgent" ». Elle
s'efface 10 s après le dernier appel d'outil.

## Solution proposée
- `StreamState` garde le dernier `agent_tool_use` (outil, entrée, horodatage).
- `lib/bureau/phraseDOutil.ts` : `Read`/`NotebookRead` → « lit <nom du
  fichier> », `Edit`/`Write`/`MultiEdit` → « édite <nom> », `Bash` → « lance
  <premier mot de la commande> », `Grep`/`Glob` → « cherche "<motif>" »,
  autre → « utilise <outil> ». **Seulement le nom du fichier**, jamais son
  chemin complet ; tronqué à 32 caractères.

## Critères d'acceptation
- [ ] `phraseDOutil` rend « lit conflits.py » pour l'entrée réelle ci-dessus, sans le chemin ; un test le vérifie
- [ ] `phraseDOutil` rend « lance pytest » pour `{"tool":"Bash","input":{"command":"uv run pytest -q"}}` — le premier mot significatif après `uv run`/`npx`/`npm run` ; un test le vérifie
- [ ] La bulle s'affiche au-dessus du poste occupé après un `agent_tool_use`, et disparaît 10 s plus tard (temps simulé) ; un test le vérifie
- [ ] Une phrase de plus de 32 caractères est tronquée par « … » ; un test le vérifie
- [ ] Le diff ne modifie aucun fichier de `backend/`