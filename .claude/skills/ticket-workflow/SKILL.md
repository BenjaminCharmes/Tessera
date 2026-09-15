---
name: ticket-workflow
description: Use when starting, committing, pushing or finishing work on a ticket — the branch/commit/push/PR sequence for this repository, including the develop integration branch.
---

# Workflow git d'un ticket

## Le flux

```
ticket-XXX-slug  ──PR──▶  develop  ──PR──▶  main
```

- **`main`** — état publiable. Ne reçoit que des merges depuis `develop`.
- **`develop`** — intégration. Cible par défaut de **toutes** les PR de ticket.
- **`ticket-XXX-…`** — une par ticket, part de `develop`.

Jamais de commit direct sur `main` ni sur `develop`.

## Démarrer

```bash
git checkout develop && git pull
git checkout -b ticket-XXX-description-courte
```

Le nom de branche reprend l'id du ticket. Déplacer le fichier du ticket dans
`tickets/in-progress/` et mettre son champ `status` à jour — les deux.

## Committer

Messages **en anglais**, Conventional Commits, type aligné sur celui du ticket.

```
fix: keep ticket branches isolated without stranding sequential work

Le corps explique le *pourquoi*, pas le *quoi* — le diff dit déjà quoi.
Nommer la contrainte réelle qui a forcé le choix.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

Préférer plusieurs commits à frontières nettes (un par préoccupation) à un
commit fourre-tout. Stager explicitement les fichiers — **jamais `git add -A`**,
qui balaie les projets importés dans `projects/` et les artefacts de travail.

## Pousser et ouvrir la PR

C'est l'étape qui a été oubliée sur ticket-045 : 13 commits sont restés locaux,
sans PR, pendant toute l'implémentation.

```bash
git push -u origin ticket-XXX-description-courte
gh pr create --base develop --title "feat: ticket-XXX — titre" --body-file -
```

**`--base develop`**, pas `main`. Le corps de PR reprend l'objectif, ce qui
change, et la vérification réellement exécutée (avec les compteurs, pas « les
tests passent »).

## Avant d'annoncer que c'est fini

```bash
cd backend && uv run pytest -q && uv run mypy src/
cd frontend && npx tsc --noEmit && npm run test -- --run
gh pr checks <n>
```

Vérifier que la CI a tourné **sur le dernier commit poussé**, pas sur un
ancien :

```bash
gh run list --branch ticket-XXX-… --limit 2 --json headSha,conclusion
git rev-parse --short HEAD
```

## Fusionner

Une fois la CI verte et la revue passée :

```bash
gh pr merge --squash --auto        # ticket -> develop : squash
```

### `develop` vers `main` : merge, jamais squash

```bash
gh pr create --base main --head develop --title "release: ..."
gh pr merge --merge                # PAS --squash
```

Un squash réécrit les SHA. Squasher `develop` dans `main` ferait diverger les
deux branches définitivement : chaque merge suivant reproduirait des conflits
sur du code déjà fusionné, et `main` perdrait l'historique par ticket — donc la
possibilité de revert un ticket précis, qui est la raison d'être de `develop`.

`develop` n'est jamais supprimée ni recréée : elle vit aussi longtemps que le
dépôt.

## Pièges connus

- **`git add -A`** balaie `projects/*` (projets importés par l'utilisateur) et
  les logs locaux. Stager nommément.
- **Réécrire l'historique** d'une branche déjà poussée : ne pas le faire sans
  décision explicite, même pour corriger un message.
- **Une PR ouverte vers `main`** alors que le flux cible `develop` : retarger,
  ne pas rouvrir une PR.

## Avant de valider

- [ ] La branche part de `develop`, pas de `main`
- [ ] Le fichier du ticket a suivi le statut réel (dossier **et** champ)
- [ ] Les commits sont en anglais, Conventional Commits
- [ ] La branche est **poussée** et la PR **ouverte**, base `develop`
- [ ] La CI est verte sur le SHA de `HEAD`
