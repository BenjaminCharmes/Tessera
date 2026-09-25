---
id: ticket-147
title: "Un panneau services dans le projet : état, adresse, logs, et quoi faire s'il n'y en a pas"
type: feat
status: done
pr_number: 166
priority: high
agent: codeur
depends_on: ["ticket-146"]
estimated_days: 1
created: 2026-09-23
---

# ticket-147 — Le panneau des services, là où on lance

## Objectif

Qu'après avoir cliqué « Lancer », il se passe quelque chose **à l'endroit où
on a cliqué** : l'état, l'adresse, les erreurs. Et qu'un projet qui ne déclare
rien dise comment en déclarer, au lieu de ne rien montrer.

## Contexte

Deux reproches au premier usage, tous deux justes.

**« Pourquoi le bouton n'apparaît plus dans fluentdb ? »** ticket-146
corrigeait « le bouton s'efface après le clic » en le faisant *ne jamais
apparaître* quand rien n'est déclaré. Ça règle le symptôme et rate le besoin :
l'utilisateur veut lancer son projet. Un bouton absent ne lui apprend même pas
que la fonction existe.

**« Toujours aucun log dans l'app quand un projet se lance ? »** La sortie
est bien captée et affichée — mais dans la vue Supervision, et seulement
après avoir cliqué sur l'étiquette d'un service. Or on lance depuis l'en-tête
du projet, où rien ne bouge. L'information existe et reste introuvable.

## Solution proposée

**Un panneau « Services » dans la colonne du projet**, sous l'en-tête, à côté
du panneau Git qui suit déjà ce motif (ouvert/fermé par son bouton).

Il montre, pour chaque service déclaré : son nom, son état, son adresse
cliquable quand il en annonce une, et ses dernières lignes. C'est là qu'on
lance, donc c'est là que le retour doit apparaître.

**Quand rien n'est déclaré**, le panneau ne disparaît pas : il explique quoi
écrire, en montrant la forme attendue, et propose d'ouvrir `agents.json` dans
VSCode — le lien existe déjà pour le projet.

Le bouton de l'en-tête reste, mais ouvre le panneau en plus de lancer : un
clic doit produire un effet visible immédiat, même avant la première ligne de
sortie.

La bande des services de la vue Supervision reste : elle sert la vue
d'ensemble, tous projets confondus. Les deux affichages lisent la même source
— `sortieDuService` — donc ils ne peuvent pas diverger.

## Critères d'acceptation

- [ ] Un test vérifie que le panneau liste les services déclarés d'un projet,
      avec leur état
- [ ] Un test vérifie qu'un projet sans déclaration affiche l'explication et
      la forme attendue, **et non un panneau vide**
- [ ] Un test vérifie que l'adresse annoncée par un service est cliquable
      depuis le panneau
- [ ] Un test vérifie que les dernières lignes d'un service s'affichent sans
      qu'on ait à ouvrir une autre vue
- [ ] Un test vérifie qu'une erreur de lancement s'affiche dans le panneau,
      texte complet, et pas seulement en infobulle
- [ ] Un test vérifie que cliquer « Lancer » ouvre le panneau
- [ ] Aucun fichier ajouté ne dépasse 200 lignes
- [ ] `npm run typecheck`, `npm run lint`, `npm run test` et `npm run build`
      passent
- [ ] Vérifié en vrai sur `fluentdb` et `ide-core`

## Dépendances

ticket-146.

## Estimation

1 jour.

## Risques

Deux endroits affichent désormais les services — le panneau du projet et la
Supervision. Ils lisent la même source, ce qui les empêche de diverger sur les
données ; reste à ne pas dupliquer leur mise en forme, sans quoi c'est celle
qu'on regarde le moins qui dérivera (ADR-034).
