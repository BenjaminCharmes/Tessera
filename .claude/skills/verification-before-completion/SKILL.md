---
name: verification-before-completion
description: Use when about to claim work is done, fixed, passing or ready to merge, and before committing or opening a PR — run the commands and read the output first.
---

# Vérifier avant d'affirmer

**Une affirmation de complétude sans sortie de commande est une supposition.**

« Les tests passent », « c'est corrigé », « la CI est verte » se prouvent. Une
seule affirmation fausse détruit la confiance dans toutes les autres.

## Les commandes

```bash
cd backend
uv run pytest -q          # attendu : "N passed", aucun failed
uv run mypy src/          # attendu : "Success: no issues found"

cd ../frontend
npm run typecheck         # attendu : aucune sortie

# `npx tsc --noEmit` ne vérifie RIEN dans ce dépôt, et c'est silencieux :
# `tsconfig.json` est un fichier « solution » (`"files": []` + `references`),
# donc tsc y trouve zéro fichier à analyser et sort sans rien dire. C'est ce
# qui a laissé 36 erreurs de types s'accumuler sans que personne les voie
# (ticket-067). `npm run typecheck` lance `tsc -b --noEmit`, qui suit les
# références.
npm run test -- --run     # attendu : "N passed"
```

Lire la **sortie**, pas le code de retour d'un œil distrait. Un `0 failed` avec
`11 skipped` inattendus n'est pas un succès.

## Ce qui ne compte pas comme vérification

| ❌ | Pourquoi |
|---|---|
| « la modification est simple » | Les plus simples cassent les tests les plus lointains |
| Avoir lancé les tests **avant** la dernière édition | Ils ne couvrent pas ce que tu viens d'écrire |
| Avoir lancé seulement le fichier de test ciblé | La régression est ailleurs |
| La CI était verte au push précédent | Elle ne dit rien du commit courant |

## Vérifier la CI sur le bon commit

`gh pr checks` peut afficher le résultat d'une exécution antérieure. Comparer
explicitement au `HEAD` local :

```bash
gh run list --branch <branche> --limit 2 --json headSha,status,conclusion \
  --jq '.[] | "\(.headSha[0:7]) \(.status) \(.conclusion)"'
git rev-parse --short HEAD
```

Les deux SHA doivent coïncider.

## Vérifier un service lancé

Un `/health` vert ne prouve pas que l'application sert. Toucher une route
réelle :

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/projects/ide-core/tickets
```

Et identifier le **processus** qui répond — un worker `--reload` orphelin
répond parfaitement en servant du code obsolète (→ `run-vibe-ide`).

## Rapporter honnêtement

- Des tests échouent → le dire, avec la sortie
- Une étape a été sautée → le dire, et pourquoi
- Une partie du périmètre est bloquée → livrer le reste **en entier**, et
  nommer ce qui manque
- Tout est fait et vérifié → l'affirmer simplement, avec les chiffres

Ne jamais présenter comme vérifié ce qui n'a pas été exécuté.

## Avant de valider

- [ ] Les quatre commandes ont tourné **après** la dernière édition
- [ ] Leur sortie a été lue, pas seulement leur statut
- [ ] Les skips et warnings sont attendus et expliqués
- [ ] La CI verte l'est sur le SHA de `HEAD`
- [ ] Ce qui est annoncé correspond exactement à ce qui a été observé
