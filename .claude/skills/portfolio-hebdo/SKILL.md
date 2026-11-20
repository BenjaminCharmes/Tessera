---
name: portfolio-hebdo
description: Use when the « portfolio hebdo » ritual is due, or when asked to update the portfolio with what the public projects shipped this week — runs the weekly report, updates project pages, and proposes an article only when the week has a real subject.
---

# Mise à jour hebdomadaire du portfolio

Le portfolio suit les projets : pages projets, articles, captures. Un texte
qui cite un chiffre faux, ou qui sonne écrit par une IA, coûte plus cher que
pas de texte. Ce skill part donc des **faits relevés**, jamais d'un souvenir.

## Avant de commencer

- **Aucune file ne tourne sur les projets concernés**, ni sur le portfolio.
  Sinon attendre la fin : un chiffre relevé pendant une file est déjà faux.
- La période : du lundi au dimanche de la semaine écoulée, sauf demande
  contraire.

## 1. Relever les faits

```bash
python scripts/releve_semaine.py --du AAAA-MM-JJ --au AAAA-MM-JJ
```

Le relevé (ticket-910) lit, par projet public : tickets approuvés et leur
titre, PR mergées, nombre de commits, lignes de `memory/faits-notables.md`.
Les projets `"confidentiality": "professional"` en sont exclus, et le
portfolio lui-même aussi.

Garder la sortie dans le scratchpad : c'est la source de chaque chiffre écrit
ensuite.

## 2. Mettre à jour les pages projets

Pour chaque projet du relevé qui a une page dans le portfolio :

- ce qui a été livré change-t-il la description, l'état ou les captures ?
- un chiffre de la page est-il devenu faux ?

Ne rien réécrire « pour rafraîchir ». Une page juste reste telle quelle.

## 3. Un article, seulement si la semaine a un sujet

Un sujet, c'est une fonctionnalité qui change l'usage, un problème résolu
qui apprend quelque chose, une mesure qui surprend. Une semaine de
corrections n'en a pas : **ne rien proposer est une issue normale.**

S'il y a un sujet : un brouillon `draft: true`, texte plus schéma ou capture,
chaque chiffre suivi de sa source (ticket, PR, ligne du relevé).

## Règles d'écriture

- `projects/portfolio/memory/style-redaction.md` s'applique à **tout** le
  contenu : pas de tiret cadratin, pas de tournures typiques d'une IA. Le
  test `articles-style.test.ts` le vérifie, le relire quand même.
- Cartes de projet : ligne 1 le titre seul, ligne 2 le badge de statut et le
  `#` de catégorie.
- Rien de professionnel : ni employeur, ni client, ni nom de projet client.

## Livrer

Tout passe par **une PR du dépôt du portfolio**, jamais un push direct. Le
titre dit la semaine couverte. Le corps liste les pages touchées et, s'il y
en a un, l'article proposé en brouillon.

Si la page d'un projet public demande une retouche de **sa** doc (README,
documentation), la demander à la session ide-core plutôt que l'écrire
soi-même.
