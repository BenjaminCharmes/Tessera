---
id: ticket-162
title: "L'anonymisation cherchait des noms d'entreprises, pas des noms de projets"
type: chore
status: in-review
pr_number: null
priority: critical
agent: codeur
depends_on: ["ticket-160"]
estimated_days: 1
created: 2026-09-25
---

# ticket-162 — Ce que l'anonymisation précédente n'avait pas cherché

## Objectif

Qu'aucune donnée professionnelle ne subsiste dans ce dépôt, et qu'un test le
vérifie au lieu d'une relecture.

## Contexte

Ticket-103 avait anonymisé le dépôt avant un passage en public. Son critère
d'acceptation disait : « `git grep` sur les **noms de clients** ne renvoie plus
rien ». Il a cherché des noms d'entreprises, les a tous trouvés, et a été
déclaré vert.

Il restait des **noms de projets** : dans deux fichiers de tests, dans trois
tickets terminés, et dans une URL de test dont le chemin reproduisait la
topologie d'une forge interne — seuls le domaine et l'organisation avaient été
remplacés. Une équipe de veille cherche exactement ces chaînes-là.

Ce n'est pas un oubli d'inattention, c'est une erreur de méthode : une liste
noire ne contient que ce à quoi on a pensé. Le premier incident (ticket-160)
portait sur une adresse e-mail que personne ne relisait ; celui-ci porte sur
des identifiants qu'une recherche pourtant explicite n'a pas couverts. Deux
fois, ce qui manquait n'était pas la vigilance mais la mesure.

## Solution proposée

1. Réécrire l'historique — `git filter-repo --replace-text` — en remplaçant
   noms de projets et fragments d'URL par des valeurs inventées, cohérentes de
   part et d'autre pour que les tests gardent leur sens. La forme testée est
   conservée : une forge auto-hébergée à sous-domaines profonds en reste une.
2. Ajouter une garde qui vérifie une **forme** et non une liste de noms : toute
   adresse e-mail du dépôt, de ses messages de commit et de ses champs d'auteur
   doit relever d'une liste blanche. Un domaine inconnu échoue, qu'on ait pensé
   à lui ou non.

La garde ne nomme aucun client, et c'est délibéré : un test qui les énumérerait
les réintroduirait dans le dépôt qu'il protège.

## Critères d'acceptation

- [ ] Aucun nom de projet client ne subsiste, sur **toute** l'histoire et
      toutes les branches
- [ ] Les URL de test gardent leur forme — sous-domaines profonds, chemin de
      groupe, compte dans l'URL Azure — sans reproduire celle d'une forge réelle
- [ ] Un test échoue sur une adresse dont le domaine n'est pas dans la liste
      blanche, dans un fichier suivi comme dans un message de commit
- [ ] La liste blanche ne contient aucun nom de client
- [ ] `uv run pytest` et `npx vitest run` passent — les remplacements sont
      cohérents entre fixtures et assertions

## Dépendances

ticket-160, qui pose ADR-043. Ce ticket en est la mesure.

## Estimation

1 jour.

## Risques

Un remplacement global peut casser un test dont la fixture et l'assertion ne
sont pas dans le même fichier. Vérifié par l'exécution des deux suites, pas par
relecture.

La liste blanche demandera un ajout le jour où un domaine légitime apparaîtra —
c'est le prix à payer pour qu'un domaine oublié échoue au lieu de passer.
