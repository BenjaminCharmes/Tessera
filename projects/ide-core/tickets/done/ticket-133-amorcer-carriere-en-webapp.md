---
id: ticket-133
title: "Amorcer la refonte de Carrière en application web multi-onglets"
type: design
status: done
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-133 — Amorcer la refonte de Carrière en application web

## Objectif

Décider ce que devient `projects/carriere/` : aujourd'hui un dossier
d'analyses, demain une application consultable depuis n'importe quel poste.

## Contexte

`projects/carriere/CLAUDE.md` dit noir sur blanc : « Ce n'est pas un projet de
code. Aucun agent n'y écrit de programme ; ils lisent des documents et
produisent des analyses. » Le manifeste déclare `codeur` et `reviewer` avec un
prompt `analyste-carriere.md`.

En faire une webapp à onglets — gérer ses compétences, préparer un entretien
annuel, etc. — ne l'étend pas : ça le **refonde**. Deux natures cohabiteraient
dans un même projet, ou il en faut deux.

Le dépôt est déjà un dépôt git local, en mode `tracked`. Le relier à un dépôt
GitHub privé est un geste de quelques minutes, pas un chantier — mais il rend
public à un service tiers un contenu qui nomme un employeur, un contrat et une
clause d'exclusivité. Ça se décide, ça ne se fait pas en passant.

## Solution proposée

Trancher, dans l'ordre :

1. Un projet ou deux ? `carriere` (analyses, agents non-codeurs) et
   `carriere-app` (le code), ou un seul avec deux jeux d'agents.
2. Ce que l'application affiche : les analyses existantes rendues lisibles, ou
   des données saisies dans l'app — ce n'est pas la même chose à construire.
3. ~~Où elle tourne~~ — **tranché : local uniquement.** L'application tourne
   sur la machine ; le dépôt GitHub privé sert de synchronisation entre les
   deux postes, pas d'hébergement. Rien de ce que contient ce projet ne monte
   chez un tiers pour être servi.
4. Ce qui part sur GitHub privé et ce qui reste local, sachant qu'ADR-021 et
   ADR-023 ont un défaut fermé et qu'il existe une clause d'exclusivité
   documentée dans le projet.

## Un onglet identifié

**Générer un CV depuis des données structurées.** Étudié comme projet
autonome, puis rattaché ici : le parcours, les compétences et les missions
vivent déjà dans ce projet, et deux endroits qui décrivent la même carrière
finiraient par diverger. Entrée déterministe, sortie déterministe — c'est
aussi l'onglet le plus facile à tester.

## Critères d'acceptation

- [ ] Une décision écrite répond aux quatre questions ci-dessus
- [ ] La décision dit si `projects/carriere/CLAUDE.md` change de nature, et le
      ticket qui l'autorisera
- [ ] La liste des onglets de l'application est arrêtée, avec pour chacun une
      phrase disant à quelle question il répond
- [ ] La décision dit explicitement quels fichiers ne doivent pas partir sur
      GitHub, même privé
- [ ] Les tickets d'implémentation sont créés dans le projet concerné, pas
      dans `ide-core`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le contenu de ce projet est sensible : contrat, rémunération, activité
freelance en parallèle d'un employeur qui exige une autorisation préalable.
« Privé » sur GitHub veut dire invisible du public, pas invisible du service.

---

## Décision — 2026-09-23

### Ce que contient réellement le dossier

La décision se prend en ayant ouvert `projects/carriere/`, pas en imaginant
son contenu :

- `sources/contrat/` — le **contrat de travail signé**, et un CV
- `sources/paie/` — **sept bulletins de paie**
- `sources/convention/` — la convention collective
- `analyses/` — dont `00-urgent-clause-exclusivite.md` et
  `08-argumentaire-reclassification.md`, préparé **contre l'employeur**

Le dépôt est local et **n'a aucun remote**.

### 4. Ce qui part sur GitHub — tranché en premier, parce que ça décide du reste

**Rien de ce dossier ne part sur GitHub. Ni privé, ni autrement.**

Un contrat signé, des bulletins de paie et un argumentaire préparé contre son
employeur ne sont pas des fichiers qu'on synchronise : « privé » veut dire
invisible du public, pas invisible du service, ni de qui obtiendrait un accès
au compte. Le bénéfice recherché était le confort de deux postes ; le risque
porte sur un litige potentiel avec un employeur. Ces deux choses ne se pèsent
pas l'une contre l'autre.

Ce n'est pas un refus de synchroniser, c'est un refus de synchroniser **ça**.

### 1. Un projet ou deux ? — Deux, et la frontière n'est pas celle qu'on croyait

Le ticket posait la question en termes de natures : documents contre code.
La vraie frontière est **ce qui a le droit de quitter la machine**. Elle est
plus nette, plus facile à tenir, et c'est celle qu'ADR-021 et ADR-023
appliquent déjà à l'intérieur d'un projet.

| Projet | Contenu | Remote |
|---|---|---|
| `carriere` | sources, analyses, agents analystes | **jamais** |
| `carriere-app` | le code, et les données structurées de CV | GitHub privé |

Conséquence : `projects/carriere/CLAUDE.md` **ne change pas de nature**. Il
reste ce qu'il dit être — « ce n'est pas un projet de code ». Aucun ticket
n'a donc à autoriser sa réécriture, ce que demandait le deuxième critère
d'acceptation : la réponse est qu'il n'y en a pas besoin.

### 2. Ce que l'application affiche

**Des données saisies dans l'app**, pas les analyses rendues lisibles.

Les analyses sont datées, argumentées, et liées à une situation précise ; les
transformer en base de données leur ferait perdre ce qui fait leur valeur. Et
les rendre depuis `carriere` obligerait l'app à lire un dossier qu'on vient
de décider de ne jamais synchroniser — l'app serait donc vide sur le second
poste, c'est-à-dire précisément là où on la voulait.

L'onglet « entretien annuel » peut lire `carriere/analyses/` **quand ce
dossier est présent sur la machine**, en lecture seule, et fonctionner sans.
Un agent a le droit de lire hors de son projet (ADR-031) ; il n'a pas le
droit d'y écrire, et c'est exactement le régime voulu.

### 3. Où elle tourne

Déjà tranché dans le ticket : **local uniquement**. Le dépôt GitHub privé de
`carriere-app` sert de synchronisation du code entre deux postes, jamais
d'hébergement.

### Les onglets

| Onglet | À quelle question il répond |
|---|---|
| **Compétences** | Que sais-je faire, à quel niveau, et quand l'ai-je pratiqué pour la dernière fois ? |
| **Missions** | Qu'ai-je fait, pour qui, et avec quelles technologies ? |
| **CV** | Comment je me présente, à partir des deux onglets précédents et d'eux seuls ? |
| **Entretien annuel** | Que vais-je demander, et sur quels éléments je m'appuie ? |

L'onglet CV est celui du ticket écarté comme projet autonome : il est ici, et
il tire ses données de `Compétences` et `Missions`. C'est ce qui empêche deux
endroits de décrire la même carrière — la raison même pour laquelle il a été
rattaché.

### Ce qui reste à toi

Une seule chose : **est-ce que même les données de CV** — compétences,
missions, formations — te vont sur un GitHub privé ? Elles sont déjà sur ton
CV, donc déjà partagées. Je l'ai supposé acceptable ; si non, `carriere-app`
reste local lui aussi et perd la synchronisation, sans rien changer d'autre.
