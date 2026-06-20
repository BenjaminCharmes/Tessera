# Stratégie CI/CD

## Workflows actifs

| Fichier     | Déclencheur                              | Rôle                     |
|-------------|------------------------------------------|--------------------------|
| `ci.yml`    | push toutes branches + PR vers `main`    | Tests + type check       |

## Stratégie par phase de tickets

### Tickets 000–002 : commits directs sur `main`

La base du projet n'est pas encore stable. Commits directs autorisés avec
message Conventional Commits (`feat:`, `fix:`, `chore:`…). La CI tourne mais
n'est pas bloquante en l'absence de PR.

### Tickets 003+ : branches + Pull Requests

À partir de ticket-003, chaque ticket est développé sur une branche dédiée :

```
git checkout -b ticket-003-agent-loop
# … travail …
gh pr create --base main
```

La PR n'est mergée que quand :
1. **CI verte** (job `test` passe)
2. **Reviewer agent approuve** (commentaire `LGTM` ou `approved` dans la PR)

Le merge peut être automatisé via GitHub Actions ou Claude Code.

## Fichiers protégés — jamais auto-mergés

Les fichiers suivants ne peuvent être modifiés que par un commit humain explicite,
même si la CI est verte et le reviewer agent a approuvé :

- `CLAUDE.md` (racine et tous les sous-projets)
- `agents.json` (tous les projets)
- `agents/prompts/**` (tous les system prompts)

Toute PR touchant ces fichiers doit être reviewée et mergée manuellement.

## Règles globales

- **Jamais de force-push sur `main`**
- Pas de merge sans CI verte (à partir de ticket-003)
- Les stubs (`return []`) sont acceptés sur `main` pendant la phase de construction
- `mypy` est non-bloquant pendant les tickets 000–004 (warn only)
