---
name: linkedin-hebdo
description: Use when the « linkedin hebdo » ritual is due, or when asked to draft a LinkedIn post about what Tessera shipped this week — reads the merged PRs, drafts one post with every figure sourced, and hands it over on the « À toi de jouer » page. Never publishes.
---

# Brouillon LinkedIn de la semaine

Le but : raconter la construction de Tessera au fil de l'eau, pour attirer du
monde vers le portfolio. Benjamin publie lui-même. Un post qui cite un chiffre
faux, ou qui sonne écrit par une IA, coûte plus cher que pas de post. Ce skill
part donc des **faits relevés**, jamais d'un souvenir, et **ne publie rien** :
ni API, ni automatisation, ni envoi.

## Avant de commencer

- La période : du lundi au dimanche de la semaine écoulée, sauf demande
  contraire.
- Lire les brouillons déjà remis sur la page « À toi de jouer » (et ceux que
  Benjamin a signalés comme publiés) : ne pas redire un sujet déjà traité.

## 1. Relever les faits

```bash
git fetch
git log --first-parent origin/develop --since=AAAA-MM-JJ --until=AAAA-MM-JJ --format="%h %ad %s" --date=short
```

Pour chaque PR qui peut faire un sujet, lire le ticket dans
`projects/ide-core/tickets/done/` : sections « Objectif » et « Ce que ça ne
fait pas », puis l'ADR citée dans `memory/decisions.md`. Garder la sortie dans
le scratchpad : c'est la source de chaque chiffre écrit ensuite.

## 2. Choisir un sujet, ou n'en choisir aucun

Un sujet : une fonctionnalité qui change l'usage, un problème résolu qui
apprend quelque chose, une mesure qui surprend, une limite découverte. Une
semaine de corrections n'en a pas : **ne rien proposer est une issue normale**,
on le dit à Benjamin en une ligne.

Une idée par post. Un essai qui conclut « non concluant » est un bon sujet : il
montre une méthode.

## 3. Écrire le brouillon

- 900 à 1 500 caractères, comptés.
- Première personne, ton d'ingénieur qui écrit à un autre ingénieur : un fait
  daté, un nombre vérifié, une erreur de jugement ou une limite assumée.
- Une question ou un lien vers le dépôt en fin de post.
- Trois hashtags au plus.
- `projects/portfolio/memory/style-redaction.md` s'applique, s'il est présent
  dans le checkout : jamais de tiret cadratin ni demi-cadratin, pas de
  « Ce n'est pas X, c'est Y », pas de formule creuse (« dans un monde où »,
  « game changer », « plongeons », « il est important de noter »), pas de
  triades par réflexe, pas d'étiquettes en gras, pas d'émojis en rafale
  (aucun, ou un seul).
- Le texte lui-même ne parle pas du texte (« dans ce post »).

## 4. Vérifier chaque chiffre

Sous le brouillon, une ligne par chiffre : **la valeur, la commande ou le
fichier qui la donne, la date du relevé.** Refaire la commande avant de remettre
le brouillon ; un chiffre qu'on ne retrouve pas sort du texte. Un nombre de
tickets se compte (`ls projects/ide-core/tickets/done | wc -l`), il ne se
rappelle pas. Une durée ou un coût vient d'un rapport du dépôt, avec son
fichier. Ce qui ne se vérifie pas dans le dépôt public n'entre pas.

## 5. Proposer un visuel, sans le produire

Une ligne : capture de l'IDE (quel écran, quel état), graphique (quelle série,
quelle source) ou schéma. Le visuel dit ce que le texte ne dit pas ; sans
visuel utile, ne pas en proposer. Pour un graphique, les teintes `data-1` à
`data-3` du dessin (ADR-047). Ne produire ni image ni capture ici.

## Rien de professionnel

Dépôt public. Dans le brouillon comme dans ses notes : ni employeur, ni client,
ni **nom de projet client**, ni e-mail professionnel, ni identifiant, ni jeton,
ni hostname interne, ni chemin personnel, ni projet privé. Un exemple
nécessaire s'invente. Le projet raconté est Tessera et ce que son dépôt public
montre.

## Remettre

Une demande sur la page « À toi de jouer » : `kind: action`, projet `tessera`.
Le titre dit la semaine couverte ; le corps porte le brouillon prêt à copier,
la liste des sources, le visuel proposé. Si la page est injoignable, déposer le
même texte dans la réponse et le dire.

Ne rien committer dans le dépôt : un brouillon LinkedIn n'est pas un fichier du
projet. Ne lancer aucun run, ne toucher à aucun service.
