---
name: menage-mensuel
description: Use when the « ménage » ritual is due, or when asked to tidy the projects' memory files — runs the housekeeping report and the pipeline-log archive, then proposes the sorting in a pull request, never deleting without consent.
---

# Ménage mensuel des fichiers de mémoire

Les fichiers de `memory/` grossissent sans que personne ne regarde. Le ménage
se fait sur une **mesure**, pas au jugé, et il **propose** : rien ne
disparaît sans accord.

## Avant de commencer

**Aucune file ne tourne** sur les projets à ranger : un run écrit son journal
et ses tickets pendant qu'on les déplace.

## 1. Mesurer

```bash
python scripts/releve_menage.py --age-jours 30
```

Le relevé (ticket-913) donne, par projet : les fichiers de `memory/` du plus
gros au plus petit, les ADR que rien ne cite, la taille et l'âge du journal,
les tickets bloqués depuis plus de 30 jours.

## 2. Archiver les journaux

Pour chaque projet dont le journal remonte à plus de deux mois :

```bash
python scripts/archiver_journal.py --projet <id> --garder-mois 2
```

Le script (ticket-912) déplace les vieux mois dans
`memory/journal/pipeline-log-AAAA-MM.md` sans perdre une ligne, et ne commite
pas. Il refuse de tourner si un run est ouvert sur le projet. Tant que le
ticket-912 n'est pas livré, le script n'existe pas : passer cette étape.

## 3. Proposer le tri

À partir du relevé, proposer, fichier par fichier :

- **archiver** ce qui ne sert plus au quotidien mais garde une valeur
  (ADR dépassées vers `decisions-archive.md`, par exemple) ;
- **fusionner** deux fichiers qui disent la même chose ;
- **raccourcir** un fichier qui se répète ;
- pour un ticket bloqué ancien : le relancer, le réécrire ou l'annuler, avec
  la raison.

Une ADR que rien ne cite n'est pas forcément morte : le relevé signale, on
tranche en la lisant.

## Livrer

Une PR par dépôt rangé, qui dit pour chaque fichier ce qui a bougé et
pourquoi. **Aucune suppression sans l'accord de Benjamin** : la PR la
propose, elle ne la fait pas. `contraintes.md`, `lecons.md` et les
`CLAUDE.md` ont leurs propres règles et budgets : ne pas les toucher ici.
