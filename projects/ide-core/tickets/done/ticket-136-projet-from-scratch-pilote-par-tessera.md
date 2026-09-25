---
id: ticket-136
title: "Choisir et lancer un projet from-scratch entièrement piloté par Tessera"
type: design
status: done
pr_number: null
priority: medium
agent: architect
depends_on: ["ticket-129"]
estimated_days: 1
created: 2026-09-23
---

# ticket-136 — Un projet from-scratch entièrement piloté par Tessera

## Objectif

Choisir un projet neuf et le faire construire de bout en bout par l'IDE, pour
voir où il tient et où il casse.

## Contexte

Tessera a construit Tessera, mais toujours sur un dépôt existant, avec des
conventions déjà posées et un humain qui rattrape. Un projet parti de rien est
le seul test qui dit si l'outil est utilisable par quelqu'un d'autre.

Ce ticket dépend de ticket-129 pour une raison simple : sans supervision, un
run de bout en bout est une suite de logs. L'intérêt de l'exercice est de
**voir** où ça coince.

## Solution proposée

Le projet à choisir doit réunir quatre propriétés, sinon l'exercice ne
démontre rien :

- **petit** — livrable en quinze à vingt tickets, pas cent ;
- **vérifiable** — des tests ont un sens dessus, sinon le pipeline ne juge
  rien ;
- **sans enjeu** — aucun contenu sensible, aucun client, un dépôt qu'on peut
  jeter ;
- **d'une stack déjà connue de l'IDE** — sinon on mesure l'ignorance du
  modèle, pas la qualité de l'orchestration.

Ce qui est à décider ici : le projet lui-même, le niveau d'`autonomy`
(ADR-029) qu'on lui donne, et surtout **ce qu'on observe**. L'exercice n'a de
valeur que si on sait d'avance ce qu'on mesure : nombre d'interventions
humaines, tickets refusés par le reviewer, coût total, tickets rejoués.

Contrainte connue à lever ou à assumer : sur `ide-core`, testeur, sécurité et
validateur sont désactivés parce que `test_command` n'atteint pas
`../../backend`. Sur un projet neuf dont les tests vivent à sa racine, rien
n'empêche de les activer — et le pipeline complet est justement ce qu'on veut
éprouver.

## Le projet retenu pour le premier exercice

**Un jeu de logique** — Wordle ou démineur. C'est celui qui tient le mieux les
quatre critères, et surtout le seul dont rien d'utile ne dépend : aucune
tentation de reprendre la main quand l'IDE se trompe, ce qui est précisément
ce qu'on veut observer. Sa logique est intégralement déterministe, donc le
testeur et le validateur ont vraiment quelque chose à juger.

Sa limite, assumée : purement frontend, il n'exerce ni le backend ni la base.

Trois autres projets sont retenus pour la suite, cadrés séparément, chacun
pour ce qu'il exerce de différent :

| | Ce qu'il met à l'épreuve |
|---|---|
| **ticket-140** — santé des dépôts | les appels d'API externes et leur mocking |
| **ticket-141** — moniteur du lab | une infra réelle, et des sondes simulées en attendant |
| **ticket-142** — habitudes et objectifs | la stack exacte de Tessera, en terrain connu |

Ils se lancent **au fur et à mesure**, jamais ensemble : l'intérêt de
l'exercice est de comparer, et des runs simultanés ne se comparent pas.

**Écartés** : un générateur de CV depuis un JSON — c'est un onglet du cockpit
Carrière (ticket-133), pas un projet, et deux endroits décrivant la même
carrière divergeraient ; un pastebin — un exercice-type sans usage réel, qui
n'apprendrait rien sur l'orchestration.

## Critères d'acceptation

- [ ] Le projet est choisi et tient en un paragraphe
- [ ] Les quatre propriétés ci-dessus sont vérifiées explicitement
- [ ] Le niveau d'`autonomy` est arrêté et justifié
- [ ] Les étapes du pipeline activées sont listées, testeur et validateur
      compris
- [ ] Les indicateurs observés pendant l'exercice sont écrits **avant** le
      premier run
- [ ] Le backlog initial est créé dans le projet neuf, pas dans `ide-core`

## Dépendances

ticket-129.

## Estimation

1 jour de cadrage. L'exécution est l'exercice lui-même.

## Risques

Le risque n'est pas que ça échoue — un échec est un résultat. C'est de ne pas
savoir dire pourquoi, faute d'avoir décidé à l'avance ce qu'on regardait.

---

## Décision — 2026-09-23

**Le projet retenu est un démineur**, et non un Wordle. Wordle dépend d'un
dictionnaire français : un actif externe à trouver, à licencier et à valider,
qui mesurerait la qualité d'une liste de mots autant que l'orchestration. Le
démineur ne dépend d'aucune donnée, et sa logique est plus riche à éprouver —
placement des mines, comptage des voisines, révélation en cascade, conditions
de victoire. Le testeur et le validateur y ont vraiment prise.

### Les quatre propriétés, vérifiées

| Propriété | Comment elle tient |
|---|---|
| Petit | 20 tickets, écrits et posés dans le dépôt |
| Vérifiable | Logique pure, déterministe, testable sans rendu |
| Sans enjeu | Aucune donnée, aucun client, un dépôt jetable |
| Stack connue | React 19, TypeScript strict, Vite, Vitest — celle de Tessera |

### Ce qui a été monté

Dépôt `BenjaminCharmes/demineur`, **privé**, relié dans `projects/demineur`
par lien symbolique comme les autres projets. Il contient un squelette qui
tourne — Vite, React, TS strict, Vitest, un test trivial qui passe, un
workflow CI — et **aucune règle du jeu**.

Cette séparation est le point méthodologique du ticket : ce qu'on mesure doit
être la construction du jeu, pas la capacité à lancer `npm create vite`. Le
squelette existe uniquement pour que le testeur ait quelque chose à exécuter
dès le premier ticket.

### Étapes du pipeline activées

Les cinq : codeur, **testeur**, **sécurité**, reviewer, **validateur**. La
contrainte qui les désactive sur `ide-core` — `test_command` qui n'atteint pas
`../../backend` — n'existe pas ici : les tests vivent à la racine du projet et
`npm run test -- --run` s'exécute depuis son dossier. C'est le pipeline
complet qu'on veut éprouver, donc il est complet.

### Niveau d'autonomie : `pr`, et pourquoi pas `merge`

`merge` était le choix de départ : sur un dépôt jetable doté d'une CI, refuser
le merge n'aurait protégé personne. Mais GitHub facture les minutes d'Actions
sur les dépôts **privés**, et la facturation de ce compte est en défaut : la
CI ne démarre pas du tout. Or `merge` exige une CI verte (ADR-029), et
l'absence de signal n'est pas un signal favorable — attendre vingt fois une CI
qui ne tournera jamais coûterait vingt attentes pour rien.

Deux façons d'y revenir, qui ne m'appartiennent pas :

1. **Rendre le dépôt public.** Les Actions y sont gratuites. Mais un dépôt
   public annonce aussi comment il est construit, et c'est exactement le choix
   de communication que le ticket-135 dit de faire exprès, pas par effet de
   bord d'un problème de facturation.
2. **Régler la facturation Actions** sur le compte.

### Ce qu'on observe

Écrit **avant** le premier run, dans `memory/mesures.md` du projet démineur.
L'indicateur principal est le nombre de tickets terminés **sans aucune
intervention humaine** : c'est la réponse à « est-ce utilisable par quelqu'un
d'autre ? ». Le protocole dit aussi ce qui invaliderait la mesure — corriger à
la main sans le consigner, ou réécrire un ticket que l'agent a mal compris,
alors que cette incompréhension **est** le résultat.

### L'ordre des projets suivants

Chacun ajoute **une** dimension et une seule, sans quoi un échec ne
s'expliquerait plus :

1. **démineur** — frontend pur, logique déterministe *(en cours)*
2. **ticket-142** — habitudes : ajoute le backend et la base, en terrain connu
3. **ticket-140** — santé des dépôts : ajoute les appels d'API externes
4. **ticket-141** — moniteur du lab : attend que le matériel existe

Jamais ensemble : des runs simultanés ne se comparent pas.
