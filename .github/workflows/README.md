# Stratégie CI/CD

## Workflows actifs

| Fichier  | Déclencheur                                | Rôle               |
|----------|--------------------------------------------|--------------------|
| `ci.yml` | PR vers `main` ou `develop` | Tests + type check |

`pull_request` seul. Une PR déclenchait autrefois **deux** runs — celui du
`push` sur la branche et celui de la `pull_request` — et tout était facturé en
double (ticket-095). Il restait ensuite un doublon sur les releases :
`push: [main]` rejouait, après le merge, ce que la PR venait de vérifier
(ticket-111).

Rien n'entre dans `main` autrement que par une PR : les commits directs y sont
interdits.

Jobs : `Backend (pytest)`, `Frontend (tsc + vitest)`, `E2E (Playwright)`,
`Ce qui a changé`, `Tauri (cargo check)` — en parallèle (ADR-015). `Ce qui a
changé` décide si le Rust a bougé : `Tauri` ne tourne que dans ce cas, une
minute de macOS étant facturée dix fois une minute d'ubuntu.

## Où tourne la CI

`runs-on` lit la variable de dépôt `CI_RUNNER`, et retombe sur `ubuntu-latest`
quand elle est vide. Les quatre jobs non-macOS la suivent ; `Tauri` reste sur
`macos-latest`, `cargo check` ayant besoin d'une chaîne Rust.

Elle existe parce que le passage du dépôt en privé (ticket-160) l'a mis face au
quota de minutes Actions des dépôts privés : plus aucune PR ne déclenchait de
run. Un runner self-hosted n'en consomme aucune.

```bash
gh variable set CI_RUNNER --body self-hosted   # basculer sur le runner local
gh variable delete CI_RUNNER                   # revenir aux runners GitHub
```

Un runner hors ligne met les jobs en file d'attente **sans fin** au lieu de les
faire échouer : si une PR reste en attente sans rien afficher, c'est la
première chose à regarder.

## Flux de branches

```
ticket-XXX-slug  ──PR──▶  develop  ──PR──▶  main
       │                     │                │
   CI par PR          CI d'intégration     release
```

- **`main`** — état publiable. Ne reçoit que des merges depuis `develop`.
- **`develop`** — intégration continue. Cible par défaut de toutes les PR de
  ticket. C'est le seul endroit où les tickets sont testés **fusionnés entre
  eux** : chaque PR est verte isolément, rien ne garantit leur combinaison.
- **`ticket-XXX-…`** — une branche par ticket, part de `develop`, y retourne.

Pas de commit direct sur `main` ni sur `develop`.

## Procédure

```bash
git checkout develop && git pull
git checkout -b ticket-XXX-description-courte
# ... implémentation ...
git push -u origin ticket-XXX-description-courte
gh pr create --base develop --title "feat: ticket-XXX — …"
gh pr merge --squash --auto          # une fois la CI verte
```

### Release : `develop` vers `main`

```bash
gh pr create --base main --head develop --title "release: ..."
gh pr merge --merge                  # merge commit, JAMAIS --squash
```

Un squash réécrit les SHA : squasher `develop` dans `main` ferait diverger les
deux branches définitivement, avec des conflits répétés sur du code déjà
fusionné, et priverait `main` de l'historique par ticket — donc de la
possibilité de revert un ticket précis.

`main` reste la branche par défaut du dépôt. `develop` n'est jamais supprimée.

## Vérifier la CI sur le bon commit

`gh pr checks` peut afficher une exécution antérieure. Comparer au `HEAD`
local :

```bash
gh run list --branch <branche> --limit 2 --json headSha,status,conclusion
git rev-parse --short HEAD
```

## Note

Le service de création de PR cible `develop` par défaut
(`settings.github_base_branch`), et la base reste paramétrable par requête.
