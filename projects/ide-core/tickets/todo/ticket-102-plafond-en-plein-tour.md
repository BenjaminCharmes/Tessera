---
id: ticket-102
title: "Un plafond atteint en plein tour ne doit pas perdre le travail"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-102 — Un plafond atteint en plein tour ne doit pas perdre le travail

## Objectif

Qu'un run stoppé par le plafond de dépense d'un appel finisse quand même par
un commit, comme tout autre run.

## Contexte

Le run du ticket-101 s'est arrêté ainsi, après 7 min 40 :

```
claude_agent_sdk._errors.ResultError:
  Claude Code returned an error result: Reached maximum budget ($1)
```

C'est `llm_max_budget_usd` (`config.py`, défaut `1.0`), qui borne **un seul
appel**. Le codeur l'a épuisé au milieu de son tour. L'exception est remontée
jusqu'à FastAPI, qui a rendu un 500.

Trois conséquences, toutes contraires à des invariants en vigueur :

1. **Aucun commit.** ADR-018 pose qu'un run finit toujours par un commit —
   typé du ticket si approuvé, `chore: … — unapproved work` sinon. Ici le
   travail du codeur est resté dans l'arbre de travail, non commité.
2. **L'arbre est resté sale**, ce qui bloque le ticket suivant : c'est
   exactement l'état qu'ADR-018 existe pour empêcher.
3. **Un run fantôme en base** : `finished_at`, `rounds`, `approved` et
   `final_status` sont restés `null`. Le run apparaît éternellement en cours.

Le plafond n'est pas en cause — il protège le quota de l'abonnement, et c'est
son rôle. Le défaut est que **son déclenchement détruit la garantie qu'il est
censé servir**.

ADR-020 définit deux plafonds, la dépense estimée et le quota réel, et pose un
invariant explicite : la vérification se fait **entre** deux tickets, parce que
s'arrêter au milieu de l'un laisserait son travail non commité. Ce troisième
plafond, interne au SDK, coupe précisément là où aucune des deux protections
ne s'applique.

ADR-030 a déjà tranché la question symétrique du côté de la livraison : une
exception y est capturée et rendue dans `Livraison.arret`, et le run garde son
résultat. Le même raisonnement n'a jamais été appliqué à la production.

## Solution proposée

1. Capturer l'échec d'un appel agent au niveau du pipeline, plutôt que de le
   laisser remonter à FastAPI. Un run interrompu est un run **non approuvé**,
   pas une erreur serveur.
2. Committer le travail déjà écrit sous `chore: … — unapproved work (…)`,
   comme ADR-018 le prévoit, en nommant la cause dans le message.
3. Clore l'enregistrement du run : `finished_at`, `final_status`, et
   `approved` à faux.
4. Rendre la cause dans la réponse pour qu'elle soit lisible dans l'IDE, au
   lieu d'un 500 opaque.
5. Décider si `llm_max_budget_usd` reste à `1.0`. Un tour de codeur sur un
   ticket de taille moyenne l'atteint : la valeur est peut-être trop basse,
   mais c'est un réglage, pas le sujet de ce ticket.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] Un test simule un `ResultError` levé par le provider pendant le tour d'un
      agent et vérifie qu'un commit est bien créé
- [ ] Ce commit porte le préfixe `chore:` et la mention `unapproved work`
- [ ] Après cet échec, `git status --porcelain` est vide sur la branche du run
- [ ] `POST /api/v1/orchestrator/run` renvoie **200** et non 500, avec un run
      non approuvé et la cause de l'arrêt lisible dans la réponse
- [ ] L'enregistrement du run a `finished_at` non nul et `approved` à faux
- [ ] Un ADR consigne la règle : un échec de production ne fait pas perdre le
      travail, symétrique d'ADR-030 pour la livraison
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Dépendances

Aucune. Le défaut est indépendant du contenu du ticket-101, qui n'a fait que
le révéler.

## Estimation

1 jour.

## Risques

Committer après un échec de production fige du travail que personne n'a relu,
parfois à moitié écrit. C'est le choix déjà fait par ADR-018 pour le travail
rejeté, et pour la même raison : un arbre sale coûte plus cher qu'un commit
mal nommé, parce qu'il bloque tout ce qui suit. Le message doit donc dire
franchement que le run a été interrompu.
