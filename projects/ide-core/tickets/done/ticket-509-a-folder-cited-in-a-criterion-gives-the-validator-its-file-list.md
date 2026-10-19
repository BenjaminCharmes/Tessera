---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-509
pr_number: 558
priority: medium
status: done
title: A folder cited in an acceptance criterion gives the validator its list of files
type: feat
---

# ticket-509 — Un dossier cité dans un critère joint au validateur la liste de ses fichiers

## Objectif
Qu'un critère du type « la maquette existe dans `design/maquette/` » soit
vérifiable par le validateur, au lieu d'être jugé invérifiable et de faire
refuser un run dont le travail est juste.

## Contexte
Le validateur ne voit que le diff, plus les fichiers que les critères citent
entre backticks (ticket-316, `backend/src/tessera/services/validator_cited_files.py`).
Une référence qui contient un `/` passe `looks_like_file`, mais un **dossier**
ne se lit pas comme un fichier : rien n'est joint.

Le 19/10, le ticket-472 a été bloqué après trois tours (environ 10 $), alors que le
validateur écrivait lui-même que les cinq critères fonctionnels étaient
couverts. Le sixième, « la maquette validée existe dans
`projects/ide-core/design/maquette/` », était vrai sur develop (PR #483) mais
invérifiable pour lui. Le critère a été réécrit à la main pour citer le fichier.

## Solution proposée
Dans `validator_cited_files.py`, une référence qui désigne un dossier
existant (sous la même racine de recherche que les fichiers) est jointe sous
la forme d'une liste : les chemins relatifs des fichiers qu'il contient, sur
un niveau, hors `_EXCLUDED_DIRS`, bornée (par exemple 100 entrées), et
comptée dans `CITED_FILES_MAX_CHARS`. Le rapport (`CitedFilesReport`) la range
dans `joined`, marquée comme dossier dans la ligne de journal
(`fichiers cités joints : design/maquette/ (dossier, 9 fichiers)`).
Un dossier absent reste dans `absent`.

## Critères d'acceptation
- [ ] Dans `validator_cited_files.py`, un critère qui cite un dossier existant entre backticks produit une section qui liste les noms des fichiers de ce dossier
- [ ] Un test vérifie qu'un dossier cité avec ou sans `/` final est reconnu
- [ ] Un test vérifie que la liste est bornée en nombre d'entrées et compte dans `CITED_FILES_MAX_CHARS`
- [ ] Un test vérifie que la ligne de journal marque l'entrée comme dossier avec son nombre de fichiers
- [ ] Un test vérifie qu'un dossier cité mais absent figure dans `absent`
- [ ] Les tests existants de `validator_cited_files` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Le contenu des fichiers du dossier n'est pas joint : seule la liste. Un critère
qui porte sur le contenu doit continuer de citer le fichier.