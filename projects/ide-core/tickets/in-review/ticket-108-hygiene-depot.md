---
id: ticket-108
title: "Le dépôt accueille correctement ceux qui arrivent"
type: docs
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-106"]
estimated_days: 1
created: 2026-09-21
---

# ticket-108 — Le dépôt accueille correctement ceux qui arrivent

## Objectif

Qu'un visiteur sache quoi faire d'un bug, d'une idée ou d'une faille, et à
quoi il s'engage en contribuant.

## Contexte

Le dépôt n'a aucun fichier d'accueil. Sur un dépôt privé c'est cohérent ; une
fois public, chaque absence a un coût :

- sans template d'issue, un rapport de bug arrive sans version, sans système
  et sans étapes de reproduction — donc sans ce qui décide s'il sera corrigé ;
- sans `CONTRIBUTING.md`, personne ne sait que la licence **n'est pas open
  source**, et quelqu'un peut écrire trois cents lignes avant de l'apprendre ;
- sans redirection, une faille de sécurité s'ouvre en issue publique, lisible
  avant qu'un correctif existe ;
- sans veille de dépendances, les mises à jour de sécurité attendent une
  vigilance manuelle qui ne se fait jamais.

## Solution proposée

1. `.github/ISSUE_TEMPLATE/` : un formulaire bug, un formulaire idée, et un
   `config.yml` qui redirige la sécurité, les questions et l'usage commercial.
2. `.github/pull_request_template.md`, qui demande la vérification **avec ses
   compteurs** — la CI ne se prononçant pas.
3. `CONTRIBUTING.md` : le flux de branches, les trois règles qui font refuser
   une PR, et surtout la nature non-OSI de la licence, dite d'emblée.
4. `CODE_OF_CONDUCT.md`, court.
5. `.github/dependabot.yml` : cadence **mensuelle** et PR groupées.

## Critères d'acceptation

- [ ] Les trois fichiers de `.github/ISSUE_TEMPLATE/` existent et sont du YAML
      valide
- [ ] `config.yml` désactive les issues vierges et redirige vers le
      signalement privé de faille
- [ ] `CONTRIBUTING.md` dit que la licence n'est pas open source et que les
      contributions relèvent de cette licence
- [ ] `CONTRIBUTING.md` reprend le flux réel : PR vers `develop`, jamais `main`
- [ ] `.github/dependabot.yml` couvre pip, npm, cargo et github-actions
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

- **Pas de `FUNDING.yml`.** Un fichier de parrainage qui pointe vers un compte
  GitHub Sponsors non configuré affiche un bouton mort. Cela se met en place
  côté compte d'abord ; le fichier suivra si vous le souhaitez.
- Pas d'automatisation d'étiquetage ni de bot d'accueil : sur un projet à un
  seul mainteneur, ils produisent du bruit avant de produire de l'aide.

## Dépendances

ticket-106 — la licence, dont `CONTRIBUTING.md` décrit les conséquences.

## Estimation

1 jour.

## Risques

Une cadence Dependabot trop rapide noierait le mainteneur unique et finirait
ignorée — une règle qu'on ignore ne protège de rien. D'où le mensuel et le
groupement par écosystème.
