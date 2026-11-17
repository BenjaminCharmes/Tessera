---
agent: codeur
depends_on:
- ticket-988
id: ticket-991
preuve_reelle: true
priority: high
status: done
title: Agent-account processes are listed by token SID, not by tasklist
type: fix
---

## Contexte

Troisième preuve réelle du 17/11 (Serpent ticket-009, run `5039a3f8`, avec
les tickets 986 et 988 actifs, poste au repos, Devinoo retenu) : le testeur
dépasse encore son délai, typecheck 85-97 s, lint 93 s, chaque étape autour de
90 s quelle que soit la commande. CPU à 1 % pendant l'attente, aucun
processus de l'agent vivant.

Cause mesurée : à la fin de chaque appel sous le compte, `clore_appel` arrête
les processus restants (ticket-943) et les listait par `tasklist /V /FO CSV`.
Sur le poste, `tasklist` résout le nom de compte de chaque processus : 87 s,
`/V` ou filtre `USERNAME` ; 1 s sans résolution. Chaque étape de test, chaque
appel de CLI, chaque lancement d'app paie ce coût fixe.

## Ce qu'il faut faire

- `providers/processus_compte.py` : le SID du compte est lu une fois
  (`LookupAccountNameW`), puis comparé à celui du jeton de chaque processus
  (`EnumProcesses`, `OpenProcessToken`, `TOKEN_USER`) ; le nom d'image vient
  de `QueryFullProcessImageNameW`. Aucun nom de compte n'est résolu.
- `droits_appel._enumerer_reel` s'en sert, hors de la boucle d'événements.
  Le parseur CSV de `tasklist` disparaît avec son test.

## Critères d'acceptation

- [x] Test : seuls les processus dont le jeton porte le SID sont gardés.
- [x] Test : une image illisible garde un nom de remplacement.
- [x] Test : ni `processus_compte.py` ni `droits_appel.py` n'appellent
      `tasklist`.
- [x] Test (Windows seulement) : le processus courant est trouvé sous son
      propre compte.

## Preuve réelle

Avant merge, sur le poste : un `node` lancé sous `tessera-agent` est trouvé
(avec son `conhost`) en 16 ms. `npm run typecheck` de Serpent sous le compte,
avec la pose et le retrait du droit d'écriture : 93,9 s avant, 9,9 s après.
Après merge et redémarrage : Serpent ticket-009 sous `tessera-agent` passe
l'étape de test dans son délai.

## Ce que ça ne fait pas

- Ne change pas la règle du ticket-943 : les restants sont toujours arrêtés,
  journalisés, à la fin du dernier appel.
- Ne voit pas un processus du compte dont le jeton ne s'ouvre pas pour le
  backend ; `tasklist` ne le voyait pas mieux sans droits admin.
