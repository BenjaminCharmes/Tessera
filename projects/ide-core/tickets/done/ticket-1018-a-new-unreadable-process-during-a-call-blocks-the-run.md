---
agent: codeur
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1018
pr_number: null
preuve_reelle: true
priority: medium
status: done
title: Scheduled tasks of the agent account are removed when its last call ends
type: fix
---

# ticket-1018 — Les tâches planifiées du compte agent se retirent à la fin du dernier appel

## Objectif

ADR-088, point 1, recadré par les essais. Rien de ce que le compte agent
planifie ne doit attendre un run suivant.

## Essais faits le 19/11, avant de coder

Sous le compte, dans un appel réel (job, sans ruche) :

- **WMI** (`Win32_Process.Create`) : refusé, code de retour 8. Aucun
  processus créé.
- **Tâche planifiée** (`schtasks /create`) : **créée**. `schtasks /run` répond
  « réussi », mais la tâche reste à l'état « Prêt » et aucun processus du
  compte n'apparaît, ni pendant l'appel ni après la fermeture du job. Le
  compte la supprime lui-même par `schtasks /delete`.
- Aucune voie de sortie du job n'a abouti. L'inventaire des processus au
  jeton illisible, prévu d'abord, n'est donc pas réalisé : il reprendrait les
  faux positifs du ticket-997 (première version : trois processus système
  nouveaux en trois minutes), et une liste blanche par nom d'image se
  contourne en nommant un programme comme un processus système.

Ce qui reste : une tâche planifiée créée par un appel survit à la clôture.
Elle ne s'est pas exécutée pendant les essais, mais elle n'a rien à faire là.

## Ce qu'il faut faire

- Nouveau module `services/providers/taches_compte.py` : `retirer_les_taches`
  lance, **sous le compte** (`lancer_sous_compte`, dossier hors worktree,
  `sans_droits=True`), `schtasks /query /fo csv /nh`, puis
  `schtasks /delete /tn <nom> /f` pour chaque tâche listée dont le nom ne
  commence pas par `\Microsoft\`. Le backend, non administrateur, ne voit pas
  les tâches d'un autre compte : c'est pourquoi la commande part sous le
  compte, avec des arguments fixés par le backend.
- Appelé par `clore_appel` au dernier appel, avant l'arrêt des processus
  restants (`services/providers/droits_appel.py`), et au démarrage du backend.
- Un code de sortie non nul sur une suppression lève `DroitsAgentRefuses`
  (ADR-037). Une liste vide n'émet aucune suppression.
- Le lanceur s'injecte, pour les tests.

## Critères d'acceptation

- [ ] Avec un faux lanceur qui rend deux tâches, dont une sous `\Microsoft\` :
  une seule suppression est émise, pour l'autre.
- [ ] Avec un faux lanceur dont la suppression rend un code non nul :
  `DroitsAgentRefuses`.
- [ ] `clore_appel` appelle `retirer_les_taches` au dernier appel seulement,
  jamais tant qu'un autre appel est actif.
- [ ] Sans `AGENT_USER`, rien n'est lancé.

## Preuve réelle

Sous le compte : un appel crée une tâche planifiée ; après sa clôture, un
second appel liste les tâches du compte et n'en trouve aucune.

## Ce que ça ne fait pas

- N'empêche pas la création d'une tâche : cela demande un droit
  d'administrateur sur le planificateur (décision de l'utilisateur).
- Ne cherche pas d'autres voies de sortie du job (BITS, non essayé).