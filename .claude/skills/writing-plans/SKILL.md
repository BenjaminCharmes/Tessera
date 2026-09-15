---
name: writing-plans
description: Use when work spans several files, several sessions or more than a handful of steps, after intent is settled and before touching code — turns a scoped problem into an ordered, verifiable plan.
---

# Écrire un plan

Un plan sert à **rester cohérent** sur un travail qui ne tient pas dans une
seule passe. Pour trois lignes dans un fichier, il coûte plus qu'il ne rapporte.

## Prérequis

L'intention est déjà cadrée (→ `brainstorming`) et un ticket existe (→
`new-ticket`). Un plan n'est pas le lieu où l'on découvre ce qu'on veut.

## Où il vit

Dans le ticket, section « Solution proposée ». C'est le seul endroit que les
agents lisent réellement.

Pour un chantier long, un fichier dédié sous `docs/` — mais le ticket reste la
source de vérité du périmètre et des critères. **Ne pas** créer un plan
parallèle qui concurrence le backlog : c'est exactement ce qui a produit les
tickets 044 et 045 sans fichier de ticket.

## Structure d'une étape

Chaque étape dit ce qui change, où, et comment on saura que c'est fait.

```markdown
### 3. Exclure les fichiers non suivis préexistants du commit

- `git_workspace.py` — capturer la liste dans `create_branch`, l'exclure
  dans `commit_all`
- Test : un fichier non suivi présent avant le run n'entre pas dans le commit
- Vérification : `uv run pytest -q tests/test_git_workspace.py`
```

Une étape sans moyen de vérification n'est pas une étape, c'est une intention.

## Ordonner

- **Ce qui débloque le reste d'abord.** Un test rouge avant le code qui le rend
  vert.
- **Une étape = un commit cohérent.** Si une étape produit trois commits sans
  rapport, la découper.
- **Isoler ce qui peut casser.** Le refactor risqué en dernier, quand la suite
  de tests le protège déjà.
- **Nommer les dépendances entre étapes**, pas seulement leur ordre.

## Dimensionner

| Signal | Réaction |
|---|---|
| Plus de ~8 étapes | Le ticket est trop gros, le découper |
| Une étape touche 10 fichiers | La découper |
| Une étape ne se vérifie pas | La reformuler jusqu'à ce qu'elle se vérifie |
| Deux étapes se disent « et aussi » | Ce sont deux tickets |

## Ce qu'un plan ne contient pas

- Le code. Un plan qui contient l'implémentation est l'implémentation.
- Des étapes « réfléchir à », « étudier » — ça, c'est `brainstorming`.
- Un périmètre ouvert. Ce qui est hors périmètre s'écrit.

## Pendant l'exécution

Le plan est un outil, pas un contrat. Si une étape révèle que le plan est faux,
**mettre le plan à jour** et le dire — ne pas dériver silencieusement, et ne
pas s'acharner sur un plan invalidé.

## Avant de valider

- [ ] Chaque étape dit comment on vérifie qu'elle est faite
- [ ] Les étapes sont ordonnées par ce qu'elles débloquent
- [ ] Aucune étape ne touche plus de fichiers qu'un commit raisonnable
- [ ] Le hors-périmètre est écrit
- [ ] Le plan vit dans le ticket, pas à côté du backlog
