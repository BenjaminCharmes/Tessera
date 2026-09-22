---
name: brainstorming
description: Use when starting any creative work — a new feature, a component, a behaviour change, a refactor with choices in it — to settle intent and constraints before writing a plan or any code.
---

# Cadrer avant de construire

Écrire du code est la partie facile. Construire la mauvaise chose coûte
beaucoup plus cher que la construire mal.

## Quand ce skill s'applique

- « ajoute X », « il faudrait pouvoir Y », « on pourrait faire Z »
- Toute feature, tout composant, tout changement de comportement
- Un refactor où plusieurs approches se défendent

**Ne s'applique pas** à un bug au comportement attendu non ambigu — là, on
reproduit puis on écrit le test qui échoue (→ `test-driven-development`) — ni
à une tâche mécanique dont la forme est déjà fixée.

## La séquence

### 1. Le problème, pas la solution

La demande arrive souvent déjà habillée en solution. Remonter d'un cran :
qu'est-ce qui ne va pas aujourd'hui ? Qui le subit ? À quelle fréquence ?

> « Il faut un chat dans l'IDE » → *que fait l'utilisateur aujourd'hui, à
> défaut ?* Il ouvre trois modales fermées et mono-tâches, ou il sort de l'IDE.

### 2. Les contraintes réelles du dépôt

Les plus coûteuses à découvrir tard sont celles qui existent déjà :

- Un invariant posé par un ADR (`memory/decisions.md`)
- Un fichier que le backend charge par son nom (`memory/decisions.md`,
  `agents/prompts/<rôle>.md`) : le renommer casse le produit, pas un test
- Un coût par appel d'agent (tout ce qui entre dans le contexte projet)
- Une garantie dont dépend autre chose (l'arbre propre d'ADR-018)

Chercher avant de proposer. Une proposition qui viole un invariant existant
sera rejetée en revue, après avoir été codée.

### 3. Deux ou trois approches, avec ce qui les disqualifie

Une seule option n'est pas un choix. Pour chacune : ce qu'elle coûte, ce
qu'elle interdit plus tard. Puis **recommander**, ne pas étaler un catalogue.

### 4. Ce qui est hors périmètre

L'écrire explicitement. Un périmètre non borné se rediscute à chaque revue.

### 5. À quoi on reconnaîtra que c'est fini

Des critères tranchables par oui/non. Ils deviennent les critères
d'acceptation du ticket (→ `new-ticket`), qui s'écrit **maintenant** : aucun
plan ni code ne démarre sans lui.

## Poser les questions qui changent le travail

Interroger seulement là où deux réponses mènent à des travaux **différents**.
Pour le reste, choisir le défaut raisonnable et le dire.

| ❌ Question inutile | ✅ Question qui tranche |
|---|---|
| Quel nom pour le fichier ? | Le chat peut-il écrire dans l'arbre suivi, ou seulement proposer un diff ? |
| On met des tests ? | On réécrit les 5 skills de process, ou les 40 des plugins ? |

## Sortie attendue

Pas du code. Un cadrage qui tient en quelques lignes :

- Le problème, en une phrase
- Les contraintes existantes qui pèsent dessus
- L'approche recommandée, et pourquoi pas les autres
- Le hors-périmètre
- Les critères de fin

Ensuite seulement : `new-ticket` pour le tracer, `writing-plans` si le travail
est long, `test-driven-development` pour l'écrire.
