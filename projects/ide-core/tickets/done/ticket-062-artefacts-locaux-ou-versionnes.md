---
id: ticket-062
title: "Artefacts vibe-ide : versionnés ou locaux, au choix du projet"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-15
---

# ticket-062 — Artefacts versionnés ou locaux

## Objectif

Qu'un projet décide si `tickets/`, `memory/`, `CLAUDE.md` et `agents.json`
partent dans son dépôt ou restent sur la machine.

## Contexte

Aujourd'hui ces fichiers sont dans l'arborescence du projet, donc commités avec
tout le reste. C'est adapté à un projet personnel — ils tracent les décisions,
survivent à la machine, se partagent.

**Ce ne l'est pas du tout pour un projet client.** Sur un dépôt freelance, les
pousser :

- encombre le dépôt de fichiers qui ne concernent pas le client ;
- expose l'organisation interne du travail ;
- laisse une trace de la méthode employée, ce que [ticket-060](../done/ticket-060-aucune-trace-ia.md)
  cherche précisément à éviter ailleurs.

Il n'y a pas de bon défaut universel : c'est une propriété **du projet**.

## Le mécanisme, et pourquoi pas `.gitignore`

Le réflexe serait d'ajouter les chemins au `.gitignore` du projet. **C'est le
mauvais outil pour un dépôt client** : `.gitignore` est lui-même versionné. Le
modifier produit un diff visible, qui annonce exactement ce qu'on voulait
taire.

Le bon mécanisme est **`.git/info/exclude`** : même sémantique, mais local au
clone et jamais commité. Rien n'apparaît dans l'historique ni dans un diff.

## Solution proposée

1. Un réglage par projet dans `agents.json` :
   `"vibe_artifacts": "tracked" | "local"`.
2. En mode `local`, les chemins vibe-ide sont inscrits dans
   `.git/info/exclude`, jamais dans `.gitignore`.
3. Le mode est **modifiable après coup**, dans les deux sens. Passer de
   `tracked` à `local` sur un projet où les fichiers sont déjà suivis exige un
   `git rm --cached` : le proposer explicitement, ne jamais le faire en
   silence.
4. `commit_all` (ADR-018) ne commite déjà que le travail du codeur et la
   comptabilité séparément — en mode `local`, la comptabilité n'a plus rien à
   commiter, ce qui doit rester sans effet sur le reste du pipeline.
5. L'UI montre le mode et permet d'en changer.

## Le défaut

**`tracked`** pour un projet créé de zéro ou importé localement — ce sont les
projets personnels, où les ADR ont de la valeur.

**`local`** pour un projet **cloné**, puisque le dépôt appartient déjà à
quelqu'un d'autre. Un défaut prudent : on peut toujours choisir de partager, on
ne peut pas défaire un push.

## Critères d'acceptation

- [x] `agents.json` porte `vibe_artifacts`, avec les défauts ci-dessus
- [x] En mode `local`, les chemins sont dans `.git/info/exclude`
- [x] **`.gitignore` du projet n'est jamais modifié**
- [x] Le mode se change dans les deux sens depuis l'UI
- [x] Passer à `local` sur des fichiers déjà suivis propose un `git rm --cached`
      et ne l'applique pas seul
- [x] En mode `local`, un run de pipeline se termine normalement
- [x] Le mode est visible dans l'UI

## Dépendances

Aucune.

## Estimation

**2j**.

## Risques

- **Moyen** — toucher à l'exclusion git d'un dépôt client. Mitigation :
  `.git/info/exclude` uniquement, jamais `.gitignore`, et aucun `git rm` sans
  action explicite de l'utilisateur.

## Livré

`services/vibe_artifacts.py` — mode par projet, exclusion entre marqueurs dans
`.git/info/exclude`, détection des artefacts déjà suivis. Endpoints
`GET/PUT /projects/{id}/artifacts`. Sélecteur dans `GitLinkPanel`.

Le clone applique `local` à la création. **ADR-021** consigne le choix du
mécanisme.

### Ce que les tests verrouillent

- `.gitignore` du projet **n'est jamais modifié**, même s'il existe déjà
- Le bloc ajouté à `.git/info/exclude` préserve ce que l'utilisateur y avait
  écrit, dans les deux sens
- Les artefacts **déjà dans l'index** sont signalés, jamais retirés : un
  `git rm --cached` modifie l'historique à venir du dépôt de l'utilisateur
