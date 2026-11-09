---
agent: codeur
created: 2026-11-09
depends_on:
- ticket-893
estimated_days: 2
id: ticket-894
plan: true
pr_number: null
priority: high
status: blocked
title: The agent CLI runs under the dedicated agent account
type: feat
---

# ticket-894 — Le CLI d'un agent tourne sous le compte dédié `tessera-agent`

## Objectif

Qu'un agent ne puisse plus lire ce que le backend protège (jeton, `.env`, coffre,
session Claude de l'utilisateur) parce que le système d'exploitation le refuse,
et non plus seulement parce qu'un garde lexical le repère.

## Contexte

L'audit externe du 06/11 a cassé deux protections par simple concaténation
(`open('agents'+'.json','w')`, chemin du jeton construit dans `python -c`) : les
gardes lexicaux expliquent, ils n'empêchent pas. Le choix retenu le 06/11 : un
compte Windows local dédié, derrière un lanceur interchangeable (un conteneur
Linux pourra le remplacer).

La phase 0 a été faite à la main le 09/11 sur le PC de Benjamin, scripts dans
`~/.tessera/worktrees/manuel/phase0-isolation/`. Sous `tessera-agent`, mesuré :
lecture du jeton de session, du `.env`, de `~/.claude/.credentials.json`, écriture
d'`agents.json`, accès au coffre et commit sont **refusés** ; l'écriture d'un
fichier source du worktree **réussit** ; `claude.exe -p` répond en 2 à 3 s, avec
stdin, stdout et stderr en tuyaux.

Ce que la phase 0 a appris, à respecter ici :
- **L'environnement ne s'hérite pas.** Sous Windows PowerShell 5.1,
  `Start-Process -Credential` transmet l'environnement de l'appelant
  (`USERPROFILE` compris) : le CLI a cherché sa configuration dans le profil de
  Benjamin. L'environnement du processus agent se construit explicitement à
  partir du profil `C:\Users\tessera-agent`, jamais copié de celui du backend.
- **L'authentification passe par un jeton.** Le `/login` interactif sous un autre
  compte n'a pas abouti. Benjamin tire un jeton longue durée par
  `claude setup-token` sous son propre compte ; il est rangé dans son coffre sous
  `AGENT_OAUTH_TOKEN` et passé au CLI dans `CLAUDE_CODE_OAUTH_TOKEN`. Changer
  d'abonnement revient à remplacer ce secret.
- **Le mot de passe du compte** est dans le coffre sous `AGENT_LOGON_PASSWORD`.
- **Le CLI** est copié dans `C:\ProgramData\Tessera\bin\claude.exe`, hors du
  profil de Benjamin, lisible et exécutable par l'agent.

## Solution proposée

Le tour de plan choisit le mécanisme de lancement (ctypes sur
`CreateProcessWithLogonW`, pywin32, ou transport SDK maison) et le justifie.
Contraintes :
- Un réglage `AGENT_USER` (vide par défaut). Vide : transport actuel, inchangé.
  Renseigné : le CLI de chaque appel `agent_sdk` démarre sous ce compte, avec
  `cli_path` vers la copie partagée.
- L'environnement du sous-processus est construit de zéro : variables système
  minimales, profil de l'agent, `CLAUDE_CODE_OAUTH_TOKEN`, plus ce
  qu'`env_sdk.py` ajoute déjà. Aucune variable du backend ne passe par défaut.
- `AGENT_LOGON_PASSWORD` et `AGENT_OAUTH_TOKEN` entrent dans `NOMS_SECRETS`
  (`backend/src/tessera/coffre.py`) ; le mot de passe n'entre jamais dans
  l'environnement de l'agent.
- Échec fermé (ADR-037) : compte absent, mot de passe ou jeton absent, logon
  refusé → `ProviderIndisponible`, run `blocked`. Jamais de repli silencieux sous
  le compte du backend.
- Les hooks `PreToolUse`, les outils MCP (`ask_user`, `signaler`) et `resume`
  passent par le protocole du SDK : ils doivent fonctionner à l'identique.

## Critères d'acceptation

- [ ] Avec `AGENT_USER` vide, le transport est celui d'aujourd'hui ; un test le
      vérifie sur la construction des options du SDK.
- [ ] Avec `AGENT_USER` renseigné, un test doublé vérifie que le lancement reçoit
      le compte, `cli_path` vers `C:\ProgramData\Tessera\bin\claude.exe`, et un
      environnement qui contient `CLAUDE_CODE_OAUTH_TOKEN` et
      `USERPROFILE=C:\Users\<compte>`.
- [ ] Un test vérifie que l'environnement de l'agent ne contient ni
      `AGENT_LOGON_PASSWORD`, ni `STATIC_TOKEN`, ni aucune variable du backend
      absente de la liste construite.
- [ ] `NOMS_SECRETS` contient `AGENT_LOGON_PASSWORD` et `AGENT_OAUTH_TOKEN`.
- [ ] Compte inexistant, mot de passe absent ou jeton absent lèvent
      `ProviderIndisponible` ; un test par cas.
- [ ] Un test d'intégration marqué `windows_only` (sauté sans compte agent)
      lance `whoami` et une lecture du fichier `.env` de Tessera sous le compte, et
      constate le nom du compte puis le refus.
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit le compte
      dédié, ce qu'il ferme (lecture des secrets, écriture des fichiers de
      politique) et ce qu'il ne ferme pas (le réseau).

## Dépendances

ticket-893 : la copie partagée du CLI doit être celle du SDK monté.

## Estimation

Deux jours.

## Risques

Le transport par tuyaux sous un autre compte est la partie la moins prouvée côté
Python ; la phase 0 ne l'a prouvé qu'avec .NET. Le plan doit prévoir un test
réel avant d'écrire le reste.

## Ce que ça ne fait pas

- Ne pose pas les droits sur les worktrees : ticket suivant.
- N'active pas `AGENT_USER` : Benjamin le renseigne quand les tickets de la
  phase 1 sont livrés.
- Ne filtre pas le réseau.