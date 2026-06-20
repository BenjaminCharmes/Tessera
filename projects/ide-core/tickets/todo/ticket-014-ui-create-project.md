---
id: ticket-014
title: "UI — Création de projet depuis la sidebar"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-013
created: 2026-06-20
---

# ticket-014 — UI Création de projet

## Contexte

Le backend expose `POST /api/v1/projects` (ticket-004 ProjectCreatorService).
Il n'existe aucun moyen depuis l'interface de créer un nouveau projet.
Ce ticket ajoute un bouton "+" dans la sidebar + un modal de création.

## Tâches

### 1. Endpoint dans `src/lib/api.ts`

```typescript
projects: {
  list: () => get<Project[]>('/projects'),
  create: (name: string, description: string) =>
    post<Project>('/projects', { name, description }),
}
```

Ajouter `post<T>()` dans le client API si pas déjà présent :
```typescript
async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}
```

### 2. `src/components/Sidebar/CreateProjectModal.tsx`

```typescript
interface CreateProjectModalProps {
  onClose: () => void
  onCreated: (project: Project) => void
}
```

Contenu du modal :
- Champ `name` (requis, placeholder "mon-projet")
- Champ `description` (optionnel, textarea)
- Bouton "Créer" → POST → onCreated(project)
- Bouton "Annuler" → onClose()
- État de chargement pendant la création
- Affichage de l'erreur si POST échoue

Styles : overlay dark semi-transparent, panneau centré 480px, cohérent avec le
thème zinc-900 de l'IDE.

### 3. Bouton "+" dans `Sidebar/index.tsx`

Dans la liste des projets (panel === 'projects'), ajouter un bouton "+" en bas
ou dans le header de la section :

```typescript
<button
  onClick={() => setShowCreateModal(true)}
  className="..."
  title="Nouveau projet"
>
  +
</button>
```

### 4. Flux complet

1. Clic sur "+" → modal s'ouvre
2. Utilisateur remplit name + description → "Créer"
3. `api.projects.create()` → POST `/api/v1/projects`
4. Backend crée le dossier + CLAUDE.md dans `projects/{name}/`
5. Modal se ferme, `useProjects` se rafraîchit
6. Le nouveau projet est auto-sélectionné

### 5. Validation inputs

- `name` : requis, pas d'espaces (format slug `kebab-case`), max 50 chars
- `description` : optionnel, max 200 chars
- Validation front uniquement pour la v0 (le backend valide aussi)

## Critères d'acceptation

- [ ] Bouton "+" visible dans la sidebar (panel projets)
- [ ] Clic → modal s'ouvre avec formulaire name + description
- [ ] Validation : name requis, pas d'espace (afficher message d'erreur inline)
- [ ] POST /api/v1/projects appelé avec le bon payload
- [ ] Après création : modal fermé, projet apparaît dans la liste, auto-sélectionné
- [ ] État de chargement pendant le POST (bouton "Créer" désactivé + spinner)
- [ ] Gestion des erreurs (nom déjà pris, erreur réseau)
- [ ] `npm run test` toujours vert (ajouter test pour CreateProjectModal)

## Notes

- Ne pas utiliser un router (pas de navigation) — modal in-place
- Le nouveau projet aura un `tickets/todo/` vide — l'utilisateur crée des tickets
  manuellement ou via agent pour la v0
- Fermeture du modal : Escape ou clic sur l'overlay
