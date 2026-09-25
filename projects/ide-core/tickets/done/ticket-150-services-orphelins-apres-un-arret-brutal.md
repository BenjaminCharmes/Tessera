---
id: ticket-150
title: "Un backend tué brutalement laisse ses services derrière lui"
type: fix
status: done
pr_number: 169
priority: high
agent: codeur
depends_on: ["ticket-149"]
estimated_days: 1
created: 2026-09-23
---

# ticket-150 — Les services orphelins

## Objectif

Qu'un service lancé par l'IDE ne survive pas sans que rien ne puisse le
retrouver ni l'arrêter.

## Contexte

**Constaté en usage réel.** Après plusieurs redémarrages du backend, l'IDE
affichait « pas lancé par l'IDE » pour `fluentdb/dev`, registre vide — alors
que **dix-sept processus** liés à ce projet tournaient encore, le plus ancien
datant de vingt-cinq minutes avant le backend courant.

ADR-042 affirme : « les processus sont des enfants du backend et meurent avec
lui — c'est ce qui rend inutile toute reprise après redémarrage. » C'est vrai
quand le backend s'arrête **proprement**, par son `lifespan`. Ça ne l'est pas
quand il est tué brutalement : le `lifespan` ne s'exécute pas, et les enfants
survivent à leur parent.

L'ADR a donc traité le cas nominal comme une garantie. C'est ce qui a permis
d'écrire « toute reprise après redémarrage est inutile », et de ne rien
prévoir.

Le symptôme est double : des processus consomment des ports sans que rien ne
les nomme, et l'écran affirme le contraire de la réalité.

## Solution proposée

Trois pistes, à trancher à l'implémentation :

1. **Retrouver ses propres orphelins au démarrage.** Le registre est en
   mémoire, donc il faudrait une trace sur disque — la liste des PID lancés,
   écrite au démarrage de chaque service. Au lancement du backend, on
   vérifie lesquels vivent encore, et on les réadopte ou on les arrête.
2. **Rendre l'arrêt inévitable côté système d'exploitation.** Sur Windows, un
   *job object* tue les enfants avec le parent, quoi qu'il arrive ; sur Unix,
   un groupe de processus joue ce rôle. C'est la seule voie qui tienne aussi
   en cas de plantage, mais elle est propre à chaque plateforme.
3. **Au minimum, ne pas mentir.** Un service déclaré dont le port répond
   pendant que le registre l'ignore doit se signaler comme tel, plutôt que
   d'afficher « pas lancé par l'IDE ».

La piste 2 traite la cause ; la 1 traite les orphelins déjà là ; la 3 est le
filet. L'ADR-042 doit être amendé dans tous les cas : sa phrase sur
l'inutilité d'une reprise après redémarrage est fausse.

## Critères d'acceptation

- [ ] Un test vérifie qu'un service lancé puis backend tué brutalement ne
      laisse aucun processus vivant — ou, si la plateforme ne le permet pas,
      que l'orphelin est retrouvé au démarrage suivant
- [ ] Un test vérifie que l'écran ne dit pas « pas lancé par l'IDE » pour un
      service dont on sait qu'il tourne encore
- [ ] ADR-042 est amendé : la garantie ne vaut que pour un arrêt propre
- [ ] `uv run pytest` et `uv run mypy src/` passent
- [ ] Vérifié en vrai : tuer le backend, le relancer, constater l'état

## Dépendances

ticket-149.

## Estimation

1 jour.

## Risques

Tuer des processus au démarrage est la manœuvre la plus destructive de tout
ce chantier : un identifiant réutilisé par le système désignerait un processus
qui n'a rien à voir. Toute reprise doit vérifier que le processus est bien
celui qu'on croit — sa ligne de commande, sa date de naissance — avant de le
toucher.
