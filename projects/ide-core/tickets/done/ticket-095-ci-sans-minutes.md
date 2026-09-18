---
id: ticket-095
title: "Travailler sans CI, et arrêter de brûler les minutes"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-094]
estimated_days: 1
created: 2026-09-18
---

# ticket-095 — La CI

## Ce qui s'est passé

Les 2 000 minutes Actions du forfait privé sont épuisées. Trois causes, toutes
réparables.

### 1. Chaque PR déclenchait deux runs

```yaml
push:         branches: ["**"]
pull_request: branches: [main, develop]
```

Une PR depuis `develop` déclenche le `push` **et** la `pull_request`. Tout
était facturé en double — visible dans `gh pr checks`, où chaque job
apparaissait deux fois.

### 2. Le job Tauri coûtait les trois quarts du budget

`runs-on: macos-latest`, et une minute de macOS est facturée **dix fois** une
minute d'ubuntu. Dix-huit secondes de `cargo check` étaient donc facturées dix
minutes. Sur un coquille Rust qui bouge une fois tous les trente tickets.

| | Avant | Après |
|---|---|---|
| Un run | 13 min | 4 min |
| Un cycle de PR | **26 min** | **4 min** |
| Cycles par mois | ~76 | ~500 |

### 3. Deux des quatre contrôles ne contrôlaient rien

```yaml
run: npx tsc --noEmit        # 0 fichier vérifié
run: uv run mypy src/ || true # erreurs avalées
```

`tsconfig.json` est de type « solution » (`files: []` + `references`) : `tsc
--noEmit` compile zéro fichier. Mesuré : **0** contre **734** pour `npm run
typecheck`.

J'avais trouvé ce piège en corrigeant les skills, et je n'avais pas corrigé la
CI elle-même. Le contrôle de types du frontend n'a donc jamais rien vérifié.

## Critères d'acceptation

- [x] `push` ne déclenche plus que sur `main` : plus de run en double
- [x] `concurrency` annule un run rendu inutile par la poussée suivante
- [x] Le job Tauri ne tourne que si `frontend/src-tauri/` a changé
- [x] En cas de doute sur la comparaison, il tourne quand même
- [x] `npm run typecheck` remplace `npx tsc --noEmit`
- [x] `mypy` n'a plus de `|| true`
- [x] `.\scripts\vibe.ps1 verify` et `make verify` enchaînent exactement les
      mêmes contrôles, en local, et s'arrêtent au premier rouge
- [x] Le skill `verification-before-completion` pointe dessus

## Conséquence sur l'autonomie

`peut_merger` exige `ci_status == "passing"` (ADR-029). Sans CI, GitHub ne
remonte aucun check, donc `none`, donc **vibe-ide ne mergera rien tout seul**.
Le défaut protège : rien de dangereux ne se produit, la livraison s'arrête à
la PR ouverte et le dit.
