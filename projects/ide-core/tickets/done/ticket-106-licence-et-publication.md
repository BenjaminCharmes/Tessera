---
id: ticket-106
title: "Le dépôt peut être public sans être repris"
type: docs
status: done
pr_number: 107
priority: high
agent: codeur
depends_on: ["ticket-103"]
estimated_days: 1
created: 2026-09-21
---

# ticket-106 — Le dépôt peut être public sans être repris

## Objectif

Publier le dépôt en gardant les droits d'exploitation, et débloquer la CI.

## Contexte

Les minutes GitHub Actions du forfait privé sont épuisées : plus aucun job ne
démarre, et la vérification se fait en local depuis le 2026-09-18 par une
dérogation écrite dans le skill `ticket-workflow`. Un dépôt **public** a des
minutes illimitées sur les runners standard.

Le déblocage tient donc à la **visibilité**, pas à la licence : le choix de
licence se fait sur son seul mérite.

Deux faits cadrent ce choix.

- **Sans licence, le code est déjà « tous droits réservés »** : le droit
  d'auteur s'applique par défaut, et public ne veut pas dire réutilisable.
  Mais beaucoup lisent « public sur GitHub » comme « libre de servir » : une
  licence explicite coupe court à cette lecture.
- **Le fork restera possible.** Publier vaut acceptation des conditions de
  GitHub, qui autorisent les autres utilisateurs à voir et forker le dépôt.
  Aucune licence ne le change ; une licence donne un recours, pas une
  barrière. Et le droit d'auteur protège le code écrit, jamais les idées.

## Solution proposée

1. `LICENSE.md` : **PolyForm Noncommercial 1.0.0**, texte officiel intégral,
   précédé de la ligne de copyright qui nomme le titulaire. Lecture et usage
   personnel permis, usage commercial interdit. GitHub la reconnaît et
   l'affiche, ce qui est précisément ce qui lève l'ambiguïté.
2. Une section « Licence » dans le `README.md`, qui dit en une phrase ce qui
   est permis — personne ne lit un texte juridique de 130 lignes.
3. `SECURITY.md` : où signaler une faille. Le produit exécute des agents sur le
   code de ses utilisateurs ; sans ce fichier, un rapport arrive en issue
   publique.
4. Une description sur le dépôt GitHub, aujourd'hui vide.

## Critères d'acceptation

- [ ] `LICENSE.md` contient les quinze sections du texte officiel, non
      modifiées, et nomme le titulaire du copyright
- [ ] `README.md` porte une section « Licence » qui dit que l'usage commercial
      n'est pas autorisé
- [ ] `SECURITY.md` existe et donne un canal de signalement privé
- [ ] Le dépôt GitHub porte une description
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

- **Ne rend pas le dépôt public.** Le basculement est un geste manuel, qui ne
  se défait pas : ce qui a été vu peut avoir été copié, archivé, indexé.
- **N'empêche pas un fork GitHub**, ni qu'on lise les idées et les
  réimplémente. Ce sont les limites structurelles du choix « public ».
- **Ne réécrit pas l'historique** (ticket-103) : les anciens commits gardent
  leurs mentions de clients.
- **Ne vaut pas un avis juridique.** Pour une exploitation commerciale, un
  professionnel reste à consulter.

## Dépendances

ticket-103 — qui a retiré les données de clients. Publier avant lui aurait
exposé ce qu'il vient de nettoyer.

## Estimation

1 jour.

## Risques

Une licence non-OSI écarte les contributions : peu de gens proposent une PR
sur un dépôt dont ils ne peuvent rien faire. C'est le prix assumé de garder
les droits d'exploitation. Le titulaire étant unique, relicencier plus tard
reste possible à tout moment — l'inverse ne l'est pas.
