# ide-core

Projet bootstrap : ce projet **est** l'IDE lui-même.
Les tickets ici décrivent les features à construire pour rendre l'IDE opérationnel.

---

## Ce qu'il faut savoir avant d'ouvrir un ticket

Les phases 1 à 10 sont livrées — quatre-vingt-dix tickets. Le détail est dans
`tickets/done/`, un fichier par ticket, et il n'a pas sa place ici : ce fichier
est `@`-importé dans **chaque** session, et une liste de travail terminé s'y
paye à chaque fois sans rien apprendre à personne.

Ce qui sert vraiment avant d'écrire du code :

- **`memory/decisions.md`** — les contraintes en vigueur. Importé lui aussi,
  donc déjà en contexte : les ignorer est un choix, pas un oubli.
- **`tickets/done/ticket-0XX-*.md`** — chacun porte une section « Ce que ça ne
  fait pas ». C'est là que sont les limites connues, et c'est ce qui évite de
  reconstruire ce qui a été écarté exprès.

## Ce qui tourne réellement sur ce projet

`agents.json` déclare `codeur` et `reviewer` dans le pipeline, et l'audit
sécurité est **actif**, sur Claude : rejoué sur une faille réelle, le modèle
local ne la voyait pas. Le validateur est **actif** depuis les tickets 209 et
214 : il juge chaque critère, lu en entier. Le testeur est **désactivé** — son
`testeur_enabled` est absent, donc faux. La documentation, elle, se met à jour
par lot en fin de file (ADR-035), jamais par ticket.

Un run approuvé pousse sa branche et ouvre sa PR vers `develop`. Il ne se
merge pas seul tant que la CI ne peut pas tourner : `merge` exige une CI verte.

Ce n'est pas un oubli à corriger à la légère : les tests de ce dépôt vivent
dans `backend/` et `frontend/`, au-dessus du dossier du projet, et
`TestRunnerService` lance sa commande depuis le dossier du projet sans passer
par un shell. Activer `testeur_enabled` demande donc un `test_command` qui
atteigne `../../backend` par lui-même. Tant que ce n'est pas fait, le dire vaut
mieux que laisser croire le contraire.

## Stack spécifique à ce projet

Identique à la stack globale. Dossier cible : `../../backend/` et `../../frontend/`

## Agents actifs sur ce projet

- `codeur` — implémente les tickets de type `feat` et `chore`
- `reviewer` — valide le code produit par le codeur
- `architect` — tient l'étape de production sur les tickets de type `design`

---

## Workflow Git

**Il n'est pas décrit ici.** Le flux — `ticket-XXX` → `develop` (squash) →
`main` (merge commit) — est dans `CLAUDE.md` à la racine, et le détail
opératoire dans le skill `ticket-workflow`.

Ce fichier a longtemps porté sa propre version, qui disait d'ouvrir les PR de
ticket sur `main` et de les merger en `--squash`. L'inverse du flux réel. Et
comme il est `@`-importé dans chaque session alors que le skill se charge à la
demande, la consigne fausse était toujours en contexte et la bonne seulement
parfois. Deux descriptions d'une même règle finissent toujours par diverger :
il n'en reste qu'une.

`test_consignes_coherentes.py` le vérifie.

---

## Lancement du projet

```bash
# Depuis la racine Tessera/
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
