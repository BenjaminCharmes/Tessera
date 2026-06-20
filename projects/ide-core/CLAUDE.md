# CLAUDE.md — projet ide-core

Projet bootstrap : ce projet **est** l'IDE lui-même.
Les tickets ici décrivent les features à construire pour rendre l'IDE opérationnel.

---

## Objectif de la v0

Un orchestrateur Python capable de :
1. Charger un projet (lire son CLAUDE.md)
2. Lister et assigner des tickets à des agents
3. Faire tourner un agent "Codeur" qui écrit du code réel
4. Faire tourner un agent "Reviewer" qui valide le code
5. Un agent "Project Creator" pour bootstrapper de nouveaux projets

L'UI vient après — la v0 est pilotable en CLI.

---

## Stack spécifique à ce projet

Identique à la stack globale. Dossier cible : `../../backend/` et `../../frontend/`

## Agents actifs sur ce projet

- `orchestrateur` — route les tickets, gère les dépendances
- `codeur` — implémente les tickets de type `feat` et `chore`
- `reviewer` — valide le code produit par le codeur
- `architect` — intervient sur les tickets de type `design`

## Agents NON actifs (pas pertinents ici)

- `redacteur` — pas de contenu éditorial sur ce projet
- `planificateur` — pas de planning calendaire

---

## Ordre d'implémentation recommandé

```
ticket-000 → ticket-001 → ticket-002 → ticket-003 → ticket-004
     ↓
Structure     Modèles      Orchestr.    Agent loop   Project
de base       tickets      FastAPI      de base      Creator
```

Ne pas sauter d'étapes — chaque ticket pose les fondations du suivant.

---

## Workflow Git

### Tickets 000–003 : commits directs sur `main`

```bash
git add <fichiers>
git commit -m "feat: description en Conventional Commits"
git push origin main
```

Pas de branche, pas de PR. La CI tourne mais n'est pas bloquante.

### À partir de ticket-004 : branche + PR

```bash
git checkout -b ticket-004-description-courte
# ... implémentation ...
git push -u origin ticket-004-description-courte
gh pr create --base main --title "feat: ..." --body "..."
# Attendre CI verte avant de merger
```

### Règles absolues

- **Jamais de `git push --force` sur `main`**
- Messages de commit en anglais, format Conventional Commits : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- Une branche par ticket (à partir de ticket-004), nommée `ticket-XXX-description-courte`
- Ne pas merger sans CI verte (à partir de ticket-004)

---

## Définition de "done" pour ce projet

Un ticket est DONE quand :
- [ ] Le code est écrit et typé
- [ ] Les tests passent (`uv run pytest`)
- [ ] Le reviewer a validé (pas de commentaire bloquant)
- [ ] La décision d'archi est documentée si pertinent
