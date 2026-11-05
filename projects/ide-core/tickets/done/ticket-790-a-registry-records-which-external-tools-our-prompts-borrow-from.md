---
agent: codeur
created: 2026-11-04
depends_on: []
estimated_days: 1
id: ticket-790
pr_number: 916
priority: medium
status: done
title: A registry records which external tools our prompts borrow from, at which commit
type: docs
---

# ticket-790 — Un registre note les outils externes dont nos consignes s'inspirent, et à quel commit

## Objectif

Quand un outil dont Tessera reprend les idées évolue, on sait quels fichiers en dérivent et
depuis quelle version, pour relire l'écart et reporter ce qui vaut.

## Contexte

La règle est de reprendre les idées d'un outil externe sans l'installer, pour ne pas en
dépendre. Benjamin, le 04/11 : « du coup, on ne suit pas forcément les évolutions des outils dont
on s'inspire ». Le ticket-715 a repris des idées de Humanizer et d'Impeccable dans
`agents/plugin/skills/design-ui/SKILL.md` et `agents/prompts/doc-fonctionnelle.md`, sans noter la
source ni la version. Personne ne peut savoir qu'il faudrait se resynchroniser.

Relevés le 04/11 avec `gh api` :
- Humanizer : `blader/humanizer`, release `v3.1.0`, commit `0ef9fe5bc357` du 28/10/2026 (dernier
  commit à la date du ticket-715, le 30/10).
- Impeccable : `pbakaus/impeccable`, release `cli-v4.8.0` du 26/10/2026, commit `df3a4abe7d08`
  (dernier commit au 30/10/2026).

## Solution proposée

- `docs/inspirations.md` : un tableau par outil source avec le dépôt, la version ou le commit
  repris, la date de reprise, le mode (`idées réécrites` ou `copie épinglée`), la licence, et les
  fichiers de Tessera qui en dérivent. Deux entrées au départ : Humanizer et Impeccable, avec les
  valeurs ci-dessus et les deux fichiers du ticket-715.
- Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` fixe la règle :
  - aucun outil externe n'est suivi en direct (pas d'installation qui se met à jour seule) : un
    skill est un texte que le modèle exécute, un changement en amont changerait le comportement
    des agents sans revue ;
  - par défaut, on réécrit les idées (`idées réécrites`) ;
  - une `copie épinglée` (texte repris tel quel, à un commit précis, avec attribution) n'est
    permise que si l'outil est du pur texte, sous licence libre compatible, sans binaire, sans
    réseau, sans télémétrie ni hook, et tient dans le budget de contexte du rôle qui le charge ;
  - toute reprise s'inscrit dans `docs/inspirations.md` ; une nouvelle version d'un outil inscrit
    donne lieu à un ticket « relire l'écart et reporter ce qui vaut », jamais à une mise à jour
    automatique.
- Un test lit `docs/inspirations.md` et vérifie que chaque fichier dérivé cité existe dans le
  dépôt.

## Critères d'acceptation

- [ ] `docs/inspirations.md` porte une entrée Humanizer (`blader/humanizer`, `0ef9fe5bc357`) et
      une entrée Impeccable (`pbakaus/impeccable`, `df3a4abe7d08`), chacune avec date, mode,
      licence et fichiers dérivés
- [ ] Les deux entrées citent `agents/plugin/skills/design-ui/SKILL.md` ou
      `agents/prompts/doc-fonctionnelle.md` comme fichiers dérivés, selon ce que chaque outil a
      inspiré
- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` décrit les deux
      modes, les conditions de la copie épinglée et l'interdiction du suivi en direct
- [ ] Un test backend vérifie que chaque fichier dérivé cité dans `docs/inspirations.md` existe,
      et échoue sur un chemin absent

## Ce que ça ne fait pas

Le suivi automatique des nouvelles versions (radar de Vigie) relève du projet Vigie : il lira ce
registre, dans un ticket de ce projet.