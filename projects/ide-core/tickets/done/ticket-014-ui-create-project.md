---
id: ticket-014
title: "UI — Création de projet depuis la sidebar"
type: feat
status: done
priority: medium
agent: codeur
depends_on:
  - ticket-013
created: 2026-06-20
completed: 2026-06-20
---

# ticket-014 — UI Création de projet ✅

## Ce qui a été fait

### `src/lib/api.ts`
- Ajout de `post<T>()` helper (réutilise `request<T>()` avec method POST)
- `api.projects.create(name, description)` → `POST /api/v1/projects`

### `src/components/Sidebar/CreateProjectModal.tsx` (nouveau)
- Champ nom (requis, no-spaces, max 50 chars) avec erreurs inline
- Textarea description (optionnel, max 200 chars)
- Spinner de chargement pendant le POST
- Affichage erreur API (ex: 409 projet existant)
- Fermeture : bouton Annuler, clic overlay, touche Escape

### `src/components/Sidebar/ProjectNav.tsx`
- Bouton `+` dans le header de la section Projects
- Après création : `refresh()` + `onSelectProject(newProject)` → auto-sélection

## Tests — 48 passing (+12)
- `CreateProjectModal.test.tsx` : 9 tests (render, validations, submit, loading, erreur API, close)
- `api.test.ts` : +2 tests (projects.create success, 409 conflict)

## PR
PR #2 mergée avec squash sur main
