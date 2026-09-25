---
id: ticket-165
title: "Le codeur promet une commande de test qu'il ne peut pas lancer"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-165 — Le codeur promet des tests qu'il ne peut pas lancer

## Objectif

Que le codeur ne s'arrête plus pour demander de lancer ce qu'une autre étape
lance déjà.

## Contexte

Premier run du banc d'essai. Le codeur écrit son code, puis :

> « Je ne dispose pas d'outil `Bash` dans cet environnement pour lancer
> `npm run test -- --run` et `npm run typecheck`. Peux-tu les lancer
> manuellement et me coller la sortie, ou confirmer que je peux supposer
> qu'ils passent ? »

Il attend **5 min 39**, personne ne répond, il reprend seul sur une hypothèse
(ADR-025). Coût : le délai complet, plus le tour repris.

Et il avait raison. Vérifié en interrogeant le provider directement :

```
« Lance 'echo TESSERA_BASH_OK' avec Bash. Sans outil Bash, réponds PAS_DE_BASH. »
→ PAS_DE_BASH
```

Alors que son prompt affirme le contraire — « `Bash` pour lancer les tests » —
et lui demande de rendre « la commande de test lancée et son résultat ». Un
prompt qui promet une capacité absente laisse deux issues : inventer la sortie,
ou s'arrêter pour demander. Le run a choisi la seconde ; rien ne garantit que
la prochaine fois sera aussi honnête.

## Ce que ce ticket ne fait pas

**Il ne rend pas `Bash` au codeur.** La cause reste ouverte : les outils sont
déclarés dans `tools` et `allowed_tools`, aucun des deux hooks `PreToolUse` ne
refuse `npm run test`, et `Read`/`Write`/`Glob` fonctionnent. Le suspect est
`permission_mode="acceptEdits"`, qui auto-approuve les écritures mais demande
une approbation pour `Bash` — approbation que personne ne donne hors session
interactive.

Le vérifier demande de basculer un agent en `bypassPermissions`, et le corriger
reviendrait à s'appuyer entièrement sur les hooks. C'est exactement ce
qu'ADR-027 décrit — ils sont le garde-fou *parce que* l'approbation précède le
callback — mais ça se décide, ça ne se glisse pas dans un correctif.

Ce ticket supprime le dommage ; la capacité fait l'objet d'une décision à part.

## Solution proposée

Le prompt du codeur décrit le contrat réel : une étape de test dédiée lance la
commande du projet (`testeur_enabled`, `test_command`), lui écrit le code et
les tests. Il ne réclame plus une sortie de commande, et ne prétend plus
disposer de `Bash`.

## Critères d'acceptation

- [ ] Le prompt du codeur ne lui attribue plus `Bash`
- [ ] Le format de sortie ne réclame plus la sortie d'une commande de test
- [ ] Le prompt dit **qui** lance les tests, pour que l'absence ne se lise pas
      comme un oubli
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Un codeur qui n'essaie plus de lancer les tests écrit moins bien ses tests —
il ne les voit jamais échouer. C'est le prix de l'état actuel, pas de ce
ticket : il ne les lançait déjà pas.
