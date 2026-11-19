---
agent: codeur
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1014
pr_number: 1190
preuve_reelle: true
priority: high
status: done
title: The agent profile wipe cannot be bypassed and fails closed
type: fix
---

## Signalement

- Audit sans contexte du 19/11, constats H1 et M2 (partie profil), suite du
  ticket-1008. Limite déjà relevée à la preuve réelle du 1008.

## Contexte

`services/providers/profil_agent.py` vide le profil partagé du compte agent à
la fin du dernier appel. Trois trous :

- Le compte est propriétaire de ce qu'il crée dans le profil et y garde
  `WRITE_DAC` : un fichier ou un dossier dont il referme la DACL, un nom
  réservé (`CON`, `x.`) ou un chemin de plus de 260 caractères font échouer
  la purge. Le run en cours passe en `blocked`, mais l'appel suivant, d'un
  autre run, démarre avec le profil piégé.
- Un profil absent ne lève rien : `reinitialiser_profil` journalise et rend
  la main, et l'appel part avec un `HOME` qui n'existe pas.
- Le dossier de profil lui-même porte « modifier » pour le compte, donc
  `DELETE` : le compte peut le déplacer.

## Ce qu'il faut faire

- Avant la purge : `icacls <profil> /setowner <backend> /T /C /L`, puis
  `/reset /T /C /L`, comme `retirer_ecriture` du ticket-1006. Le droit du
  compte et une ACE OWNER RIGHTS `(OI)(CI)(RC)` se reposent après, l'ACE du
  backend d'abord (leçon du 1006).
- La purge passe par des chemins à préfixe long de Windows (noms réservés,
  chemins de plus de 260 caractères).
- Profil absent sous `AGENT_USER` : `DroitsAgentRefuses`, plus un simple
  avertissement.
- `ouvrir_appel` refuse (`DroitsAgentRefuses`) tant que le dernier nettoyage
  a échoué : un indicateur de module, remis à zéro par un nettoyage réussi.
- `scripts/agent-setup-admin.ps1` : le droit du compte sur le dossier de
  profil ne porte que sur son contenu (`(OI)(CI)(IO)M`), plus lecture et
  création sur le dossier lui-même, sans `DELETE`.

## Critères d'acceptation

- [ ] Avec un faux `Icacls` : `reinitialiser_profil` émet `/setowner` puis
  `/reset` avant de purger, puis repose le droit du compte et l'ACE
  `*S-1-3-4:(OI)(CI)(RC)`.
- [ ] Test : un profil absent lève `DroitsAgentRefuses`.
- [ ] Test : après un nettoyage en échec, `ouvrir_appel` lève
  `DroitsAgentRefuses` ; après un nettoyage réussi, il passe.
- [ ] Test (Windows, ignoré ailleurs) : un fichier nommé `x.` et un chemin de
  plus de 260 caractères dans un profil de test sont supprimés.
- [ ] Sans `AGENT_USER`, rien n'est émis ni refusé.

## Preuve réelle

Sous `AGENT_USER` : un appel crée dans son profil un dossier dont il retire
tous les droits sauf les siens, puis un fichier `x.`. Constater le refus de
la DACL (OWNER RIGHTS) ou, à défaut, que la clôture reprend et supprime le
tout ; puis qu'un profil renommé à la main bloque l'appel suivant avec
`DroitsAgentRefuses` nommé.

### Faite le 19/11, sur le poste, sous le compte agent

Ajouté à la main avant la preuve : une ouverture d'appel retente le
nettoyage quand le dernier a échoué (aucun autre appel en cours), au lieu de
tout refuser jusqu'au redémarrage du backend.

- Un appel crée un dossier dans son profil et tente d'en couper l'héritage :
  refusé (code 5, OWNER RIGHTS). Il crée un fichier `x.` et un chemin de
  344 caractères : tout est purgé à la clôture, il ne reste que `AppData`,
  `npm-cache` et `uv`. Il tente de déplacer le profil : refusé.
- Profil renommé à la main : l'appel lève `DroitsAgentRefuses` (« profil de
  l'agent absent »), et le suivant est refusé de même.
- Profil remis en place : l'appel suivant retente le nettoyage et passe,
  sans redémarrage.

## Ce que ça ne fait pas

- Ne traite pas les caches gardés (ticket-1016).
- Ne retire pas le compte du groupe des utilisateurs (ticket-1016).