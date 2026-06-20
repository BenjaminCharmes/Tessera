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

## Définition de "done" pour ce projet

Un ticket est DONE quand :
- [ ] Le code est écrit et typé
- [ ] Les tests passent (`uv run pytest`)
- [ ] Le reviewer a validé (pas de commentaire bloquant)
- [ ] La décision d'archi est documentée si pertinent
