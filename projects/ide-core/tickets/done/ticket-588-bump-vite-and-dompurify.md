---
id: ticket-588
title: "Bump vite and dompurify past their published advisories"
type: chore
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-26
---

# ticket-588 — vite et dompurify passent les avis publiés

## Objectif
Fermer les avis GHSA que le radar de Vigie signale sur deux dépendances du
frontend (édition 2026-W44). Retouche faite à la main, hors pipeline.

## Contexte
- `dompurify` 3.4.16, et 3.4.15 embarqué par `monaco-editor`, qui le fige :
  GHSA-cg2g-xh64-v4q7 (critical), GHSA-mrv2-3pqr-j5jr (high),
  GHSA-c6gr-qvv4-5v3f (low), corrigés en 3.4.17. `MarkdownView.tsx` appelle
  `sanitize` avec le seul profil `html` et une sortie en chaîne : aucun des
  trois chemins (`SAFE_FOR_TEMPLATES`, `IN_PLACE`, parseur XHTML) n'y passe.
  La copie de Monaco, elle, sert à ses survols.
- `vite` 8.3.1 : six avis sur le serveur de dev, dont un *high* dans
  `launch-editor` propre à Windows ; corrigés en 8.3.3.

## Solution proposée
- `dompurify` ^3.4.17, `vite` ^8.3.5.
- Un `overrides` npm aligne la copie de `monaco-editor` sur la version de
  `dompurify` du projet (`$dompurify`).

## Critères d'acceptation
- [x] `npm ls dompurify` ne montre que 3.4.17, Monaco compris
- [x] `npm ls vite` montre 8.3.5
- [x] Le diff ne modifie que `frontend/package.json`, `frontend/package-lock.json` et ce ticket

## Ce que ça ne fait pas
- Ne touche pas aux dépendances que le radar dit « stale » (`httpx`,
  `pytest-xdist`, `@monaco-editor/react`) : leurs dépôts sont actifs.
