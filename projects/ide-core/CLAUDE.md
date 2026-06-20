# CLAUDE.md — projet ide-core

Projet bootstrap : ce projet **est** l'IDE lui-même.
Les tickets ici décrivent les features à construire pour rendre l'IDE opérationnel.

---

## État de la v0

### Phase 1 — Backend : ✅ DONE (tickets 000–006)

1. Structure de base et configuration
2. Modèles Pydantic + TicketService
3. ProjectLoader + API projets/tickets
4. Agent loop avec streaming Claude
5. Orchestrateur multi-agents (codeur→reviewer, max 3 tours)
6. GitHub Sync (import issues → tickets)

### Phase 2 — Frontend + Desktop : ✅ DONE (tickets 007–010)

7. Scaffold React/Vite/Tailwind/Monaco
8. Ticket board (liste + kanban)
9. Agent stream panel (WebSocket)
10. Tauri v2 shell (fenêtre native macOS)

### Phase 3 — Qualité + UX : 🚧 EN COURS (tickets 011–015)

11. Monaco branché sur le filesystem réel
12. Tests frontend (Vitest + RTL, 80% couverture)
13. CI GitHub Actions (3 jobs parallèles)
14. UI création de projet depuis la sidebar
15. SQLite persistence (historique des pipelines)

---

## Stack spécifique à ce projet

Identique à la stack globale. Dossier cible : `../../backend/` et `../../frontend/`

## Agents actifs sur ce projet

- `orchestrateur` — route les tickets, gère les dépendances
- `codeur` — implémente les tickets de type `feat` et `chore`
- `reviewer` — valide le code produit par le codeur
- `architect` — intervient sur les tickets de type `design`

---

## Workflow Git

### Workflow selon la phase

**Avant ticket-013 (CI)** : commit direct sur `main`. Les PRs sans CI n'apportent rien pour un projet solo.

**Après ticket-013 (CI opérationnelle)** : une branche par ticket + PR obligatoire.
```bash
git checkout -b ticket-XXX-description-courte
# ... implémentation ...
git push -u origin ticket-XXX-description-courte
GH_CONFIG_DIR=/Users/moi/.config/gh gh pr create --base main --title "feat: ticket-XXX — ..."
# Attendre CI verte avant de merger
```

### Règles absolues

- **Jamais de `git push --force` sur `main`**
- Messages de commit en anglais, format Conventional Commits : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`

---

## Lancement du projet

```bash
# Depuis la racine vibe-ide/
make dev              # Lance FastAPI sur http://localhost:8000
make dev-frontend     # Lance Vite sur http://localhost:5173
make tauri-dev        # Lance l'app desktop (nécessite make dev dans un autre terminal)
make test             # Lance les tests Python
make lint             # Type-check mypy
```

---

## Définition de "done" pour ce projet

Un ticket est DONE quand :
- [ ] Le code est écrit et typé (strict TypeScript / type hints Python)
- [ ] Les tests passent (`uv run pytest` backend, `npm run test` frontend)
- [ ] `npm run build` + `cargo check` passent sans erreur
- [ ] La décision d'archi est documentée si pertinent
