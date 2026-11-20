---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-946
pr_number: null
priority: high
status: done
title: The agent CLI starts under the agent account despite the 1024-character command-line
  limit
type: fix
---

# ticket-946 — Le CLI d'un agent démarre sous le compte dédié malgré la limite de 1 024 caractères

## Objectif

Qu'un vrai appel d'agent démarre sous `AGENT_USER`. Aujourd'hui, aucun ne le
peut.

## Contexte

Premier run réel sous le compte dédié, le 12/11 (serpent, ticket-009,
`worktree.compte_agent: true`). `npm ci` passe, puis le codeur s'arrête :
« INTERROMPU au tour 1 — ProviderIndisponible: logon du compte tessera-agent
refusé : erreur Windows -2147024809 » (`0x80070057`, ERROR_INVALID_PARAMETER).
Le run a fini en `blocked`, sans repli sous le compte du backend (ADR-037
respecté).

Cause : `lanceur_windows.py` passe toute la ligne de commande du CLI
(`subprocess.list2cmdline`) en `lpCommandLine` de `CreateProcessWithLogonW`.
La documentation Windows la limite à **1 024 caractères**. Celle du CLI
Claude (prompt système, outils permis, config MCP, réglages) la dépasse de
loin. Les tests des tickets 894 et 934 utilisent un lanceur double, et la
preuve de la phase 0 lançait des commandes courtes : personne n'avait encore
lancé un vrai CLI sous ce compte. La commande de test d'un projet (ADR-085)
tient en général sous la limite.

`message_de_logon` présente toute erreur comme un logon refusé, ce qui a
égaré le diagnostic.

## Solution proposée

1. Avant le lancement sous compte, les valeurs longues de la commande
   (prompt système, config MCP, réglages, liste d'agents) passent par des
   fichiers, avec les options du CLI qui les lisent depuis un fichier. Ces
   fichiers sont écrits dans un dossier par appel, lisible par le compte
   agent et non modifiable par lui, puis supprimés à la fin de l'appel.
2. Si la ligne dépasse encore 1 024 caractères, `ProviderIndisponible`
   nomme la cause : « ligne de commande de N caractères, au plus 1 024 ».
3. `message_de_logon` distingue ERROR_INVALID_PARAMETER, ERROR_LOGON_FAILURE
   et ERROR_ACCESS_DENIED.

## Critères d'acceptation

- [x] Un test : pour une commande de codeur réaliste (prompt système de
      plusieurs kilo-octets), la ligne passée au lanceur fait au plus
      1 024 caractères.
- [x] Un test : une ligne de plus de 1 024 caractères est refusée avant
      l'appel Windows, avec un message qui donne sa longueur.
- [x] Un test : `message_de_logon(-2147024809, …)` ne parle pas de logon
      refusé.
- [x] Un test : les fichiers de l'appel sont supprimés après la fin du
      processus, et même en cas d'échec du lancement.
- [x] Preuve sur la machine, notée dans le ticket à la livraison : un run
      serpent sous `tessera-agent` atteint la revue.

## Ce que ça ne fait pas

- Ne change pas le compte ni ses droits (tickets 943 et 944).
- Ne touche pas aux projets sans `worktree.compte_agent`.

## Livraison (12/11, fini à la main)

Le run du pipeline s'est bloqué au tour 3 : le reviewer demandait un test du
nettoyage après un lancement réussi (ajouté :
`test_call_files_outlive_a_successful_launch_and_vanish_on_close`), et le
validateur ne pouvait pas juger le critère de preuve sur la machine.

Preuve réelle, faite par la session ide-core avec ce code : un vrai CLI
(`claude-haiku-4-5`, prompt système de plus de 2 000 caractères) lancé par
`ClaudeAgentSDKProvider(compte_agent=True)` répond ; `whoami` →
`tessera-agent` ; lecture du `.env` de Tessera refusée ; `preuve.txt` écrit,
propriétaire `tessera-agent`. Condition : le dossier de travail était hors du
profil de l'utilisateur (`C:\ProgramData\Tessera\…`). Sous
`~/.tessera/worktrees`, le CLI refuse d'écrire (« chemin non résolvable ») :
le compte ne peut pas lire les attributs des dossiers du profil. Un run serpent
n'atteindra donc la revue qu'avec le ticket-947. Constaté aussi :
`agent_non_rattache` (OpenProcess refusé), comme l'annonçait le ticket-943.

