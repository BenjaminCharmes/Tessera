---
id: ticket-929
title: "The secret read guard also covers the Claude subscription session, git credentials and the GitHub CLI hosts file"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-928"]
estimated_days: 0.5
created: 2026-11-11
---

# ticket-929 — La garde de lecture couvre aussi la session de l'abonnement, les identifiants git et le fichier d'hôtes de `gh`

## Objectif

Qu'un agent ne lise pas les fichiers du compte du backend qui donnent accès à
l'abonnement Claude, aux dépôts git ou à GitHub.

## Contexte

Audit du 11/11, vérifié sur `origin/develop` : `hook_refus_env_tessera`
(`backend/src/tessera/services/providers/garde_jetons.py`, l. 218-225) ne
garde que le `.env` de Tessera, le fichier du jeton de session et les
`.env*.local` du frontend. ADR-031 laisse lire hors du projet : sans compte
dédié (ticket-915, `worktree.compte_agent`), l'agent tourne sous le compte du
backend et lit librement :

- `~/.claude/.credentials.json` — la session de l'abonnement Claude ;
- `~/.git-credentials` — les identifiants du helper `store` de git ;
- `%APPDATA%\GitHub CLI\hosts.yml` sous Windows, `~/.config/gh/hosts.yml`
  ailleurs (ou `$GH_CONFIG_DIR/hosts.yml`) — le jeton de `gh` quand il n'est
  pas dans le coffre.

## Solution proposée

- Ajouter ces chemins à `cibles`, résolus **une fois, à la fabrication du
  hook**, depuis le compte du backend (`Path.home()`, `%APPDATA%`,
  `GH_CONFIG_DIR`) : sous `AGENT_USER`, `~` désigne un autre dossier, et ce
  sont les fichiers du backend qu'on garde.
- Un message de refus propre à ces fichiers, sur le modèle de `JETON_REFUS` :
  ce qui est refusé, et que la garde attrape une erreur, pas une évasion.
- Un fichier absent reste gardé : son chemin est connu, le créer plus tard ne
  doit pas l'ouvrir.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_garde_jetons.py` vérifie qu'un `Read` de
      `<home>/.claude/.credentials.json` est refusé, le dossier personnel
      redirigé vers un dossier temporaire.
- [ ] Un test vérifie qu'un `Bash` `cat ~/.git-credentials` est refusé.
- [ ] Un test vérifie qu'un `Read` du `hosts.yml` de `gh`, dans le dossier
      que la plateforme du test lui donne, est refusé.
- [ ] Un test vérifie qu'un `Read` de `<home>/.claude/settings.json` passe.
- [ ] Le message de refus de ces fichiers dit que la garde attrape une
      erreur, pas une évasion.

## Ce que ça ne fait pas

- Ne garde ni `~/.ssh/`, ni `~/.netrc`, ni le gestionnaire d'identifiants de
  Windows (dont l'exécution est déjà refusée par `garde_coffre.py`) : hors du
  constat d'audit ; le vrai plafond est le compte dédié, dont le dossier
  personnel ne porte aucun de ces fichiers.
- Ne ferme pas un chemin construit en deux temps (ADR-031).

## Dépendances

ticket-928 : même module, et la normalisation des chemins `\\?\` doit valoir
aussi pour ces cibles.

## Estimation

Une demi-journée.

## Risques

Le plafond de 300 lignes de `garde_jetons.py` : les chemins gardés peuvent
vivre dans un petit module de constantes.
