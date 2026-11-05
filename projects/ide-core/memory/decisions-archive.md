# Décisions d'architecture — archive

Les ADR qui ne contraignent plus rien : le code qu'ils décrivaient n'existe
plus, ou un ADR postérieur les a explicitement remplacés — une ADR remplacée
porte une ligne `**Remplacée par**`. S'y trouvent aussi celles qu'aucune
règle de `contraintes.md`, ni `CLAUDE.md`, ni `projects/ide-core/CLAUDE.md`
ne cite plus : un test les refuse dans `decisions.md` (ticket-830).

**Ce fichier n'est importé par aucun `CLAUDE.md` et n'est injecté dans aucun
appel d'agent.** Il est ici pour qu'on retrouve *pourquoi* une décision a été
prise, le jour où la question se repose — pas pour être lu à chaque run.

Les numéros ne sont jamais réattribués : un ADR archivé garde le sien, et
aucun ADR futur ne le reprend.

---

## ADR-016 — Scope filesystem Tauri : $HOME pour la v0

**Date** : 2026-06-20
**Portée** : architect  
**Décision** : Le plugin `tauri-plugin-fs` a accès à `$HOME/**` en v0.
**Raison** : Les projets Tessera seront dans `~/` (dossier utilisateur). Scope plus restrictif nécessiterait de connaître le chemin exact au build time.
**Alternative rejetée** : Scope filesystem complet `/` (trop large, rejeté par App Store), scope fixe `~/tessera-workspace/` (impose un emplacement).

---

**Remplacée par** : ADR-040  
**Archivé le 2026-09-23 (ticket-131)** — remplacé par **ADR-040** : l'app
Tauri n'expose plus aucune permission `fs:*`, donc il n'y a plus de scope
filesystem à définir. Le contrôle de chemin vit entièrement dans
`routers/fs.py`, côté backend.

---

## ADR-001 — Self-hosting comme premier projet

**Date** : 2025-06  
**Portée** : architect  
**Décision** : L'IDE se construit lui-même via le projet `ide-core`  
**Raison** : Évite de maintenir deux systèmes séparés. L'IDE mange sa propre cuisine dès le départ, ce qui force à le rendre utilisable rapidement.  
**Alternative rejetée** : Écrire l'IDE "à la main" puis le brancher après.

---

## ADR-002 — Pas de framework agent externe

**Date** : 2025-06  
**Portée** : architect  
**Décision** : On implémente notre propre agent loop (pas LangChain, CrewAI, etc.)  
**Raison** : Ces frameworks changent d'API tous les 6 mois. On veut contrôler le protocole de communication entre agents (JSON-RPC), la gestion des tickets, et la mémoire.  
**Alternative rejetée** : LangGraph (trop couplé à l'écosystème LangChain).

---

## ADR-003 — Tickets comme fichiers Markdown

**Date** : 2025-06  
**Portée** : architect  
**Décision** : Les tickets sont des fichiers `.md` avec frontmatter YAML, pas une DB  
**Raison** : Lisibles sans l'IDE, versionnables avec git, diffables. La DB vient en couche de cache au-dessus, pas comme source de vérité.  
**Alternative rejetée** : SQLite comme source de vérité pour les tickets.

---

## ADR-004 — Tauri plutôt qu'Electron

**Date** : 2025-06  
**Portée** : architect  
**Décision** : Shell desktop en Tauri v2  
**Raison** : Bundle 10x plus léger, accès filesystem natif sécurisé, Rust pour les parties critiques. Microsoft lui-même cherche à sortir d'Electron sur VS Code.  
**Alternative rejetée** : Electron (trop lourd), app web pure (pas d'accès filesystem).

---

## ADR-005 — uv comme gestionnaire Python

**Date** : 2025-06  
**Portée** : architect  
**Décision** : `uv` pour toute la gestion des dépendances Python  
**Raison** : 10-100x plus rapide que pip, résolution de dépendances déterministe, remplace pip + venv + poetry en un seul outil.  
**Alternative rejetée** : Poetry (lent), pip (pas de lock file natif).

---

## ADR-011 — httpx natif plutôt que PyGitHub pour l'API GitHub

**Date** : 2026-06  
**Portée** : architect  
**Décision** : `GitHubService` utilise `httpx` async directement (déjà dépendance du projet).  
**Raison** : PyGitHub est synchrone et ajoute une abstraction lourde. On n'utilise que 3 endpoints (list issues, add label, remove label). httpx + respx donne des mocks propres en tests.  
**Alternative rejetée** : PyGitHub (blocking I/O), gidgethub (trop orienté webhooks).

---

## ADR-015 — CI : des jobs parallèles, et macOS seulement si Tauri change

**Date** : 2026-06-20
**Portée** : architect  
**Décision** : cinq jobs — `detecter`, `backend` (ubuntu, pytest), `frontend` (ubuntu, tsc+vitest), `e2e` (Playwright) après `frontend`, et `tauri` (macos, `cargo check`) qui ne tourne que si `detecter` voit `frontend/src-tauri/` changer.
**Raison** : responsabilités séparées et exécution parallèle donnent un retour rapide. `macos-latest` est requis par Tauri (headers WKWebView) mais une minute y vaut dix minutes d'ubuntu — pour dix-huit secondes de `cargo check`, le conditionner paie. `cargo check` et non `cargo build` : dix minutes de compilation évitées.
**Alternative rejetée** : job unique séquentiel (lent) ; `cargo build` complet (coûteux) ; `tauri` inconditionnel — facturé à chaque PR sans rien apprendre.

---

## ADR-032 — Un ADR déclare qui il contraint

**Date** : 2026-09-18
**Portée** : architect
**Décision** : un ADR peut porter `**Portée** : rôle, rôle` ; `services/adr.py` réduit alors la section « Décisions récentes » du prompt aux ADR qui concernent le rôle appelé. **Sans portée, l'ADR part à tous.** Elle ne s'écrit que sur un ADR qui enregistre un choix passé, jamais sur une contrainte de comportement — un test le verrouille.
**Raison** : le fichier part dans chaque appel d'agent, jusqu'à dix-huit par ticket. Le coût compte, la dilution davantage : un codeur recevait la palette de couleurs et le choix du gestionnaire de paquets Python au milieu des règles qu'il doit tenir.
**Ce qui rend la règle sûre** : un agent que l'utilisateur vient de créer n'est nommé nulle part, et reçoit malgré tout tout le tronc commun — donc toutes les contraintes.

---

## ADR-034 — Une règle n'est décrite qu'à un endroit, et ce qui compte est mesuré

**Date** : 2026-09-18
**Portée** : architect
**Décision** : une règle a **une** description ; les fichiers de consigne renvoient à elle au lieu de la reformuler. `test_consignes_coherentes.py` vérifie qu'ils ne se contredisent pas sur git, ne codent en dur aucun chemin de machine, ne décrivent rien d'absent, et qu'aucun ADR ne dépasse son budget.
**Raison** : `projects/ide-core/CLAUDE.md` portait sa propre version du flux git — PR de ticket sur `main`, merge en `--squash` — l'exact inverse de la règle. Il est `@`-importé dans chaque session quand le skill juste se charge à la demande : la consigne fausse était toujours en contexte, la bonne seulement parfois.
**Corollaire** : un budget que rien ne mesure est un souhait. Douze ADR sur trente et un dépassaient le leur, dont trois écrits le jour où ce budget était rappelé.

---

## ADR-036 — Une clef de manifeste se renomme en gardant la lecture de l'ancienne

**Date** : 2026-09-21
**Portée** : architect
**Décision** : le produit s'appelle Tessera. Les identifiants portant l'ancien nom sont réécrits, **sauf** `vibe_artifacts` dans `agents.json` : la clef devient `artifacts`, l'ancienne reste lue, jamais réécrite.
**Raison** : des manifestes la déclaraient déjà sur disque, dont des dépôts que ce dépôt ne versionne pas. Une clef inconnue tombe sur le défaut fermé d'ADR-023 : un projet en `tracked` serait repassé en `local` sans demande et sans message. Le renommage aurait donc changé un comportement qu'il prétendait préserver.
**Alternative rejetée** : migrer les manifestes d'office — écrire dans un dépôt tiers pour une question cosmétique ; garder les deux clefs en écriture — elles divergeraient.
**Conséquence assumée** : le nom d'origine survit dans une constante et ses tests. C'est le prix d'une donnée déjà écrite ailleurs.

---

## ADR-052 — Séparer le journal des contraintes en vigueur

**Date** : 2026-10-02
**Portée** : architect
**Décision** : `memory/decisions.md` reste le journal complet. `memory/contraintes.md` en extrait les règles actives, regroupées par thème, une ou deux phrases à l'impératif. `memory/adr-audit.md` classe chaque ADR (règle, histoire, obsolète, fusion). Les agents liront `contraintes.md` à la place du journal une fois ticket-311 livré.
**Raison** : le journal fait 43 Ko et 51 ADR ; un codeur en reçoit 39 après filtrage par portée. La moitié raconte *pourquoi* un choix a été fait, pas ce qu'un agent doit faire. Les règles de design (ADR-026, ADR-047) ont été régulièrement ignorées — une règle noyée dans un journal se lit mal.
**Alternative rejetée** : raccourcir `decisions.md` — on perd l'histoire et la justification ; n'archiver que les ADR obsolètes — la dilution reste, la taille change peu.

---

## ADR-054 — Proposer des tickets passe par un worktree temporaire, et le CIWatcher merge

**Date** : 2026-10-18
**Décision** : `POST /api/v1/projects/{id}/tickets/propose` valide le lot avant la configuration GitHub, puis écrit dans un worktree temporaire créé depuis `origin/<base>` : commit, push, PR vers la base, worktree supprimé même si le push échoue. L'arbre principal n'est jamais touché ; le `fetch` ne met à jour que `refs/remotes/origin/<base>`. Le merge n'a pas lieu dans la requête : en `autonomy: merge`, la PR est remise au `CIWatcher`, sinon elle reste ouverte.
**Raison** : la route sert quand un run tient l'arbre. Une requête HTTP n'attend pas une CI (ADR-051).
**Alternative rejetée** : merge synchrone dans la requête — bloque sur la CI (ADR-029).

---

## ADR-060 — Un ticket non mergé n'arrête que ceux qui en dépendent

**Date** : 2026-10-27
**Décision** : complète ADR-051. Quand un ticket de la file n'est pas mergé, les tickets restants qui en dépendent par `depends_on`, directement ou par transitivité, sont retirés de la file ; chacun s'écrit dans `memory/pipeline-log.md` avec sa dépendance (« ticket-546 sauté : dépend de ticket-544, non mergé »). La file continue avec les autres et ne s'arrête que s'il ne reste plus rien. Le ticket non mergé reste `blocked`, PR ouverte, comme dans ADR-051.
**Raison** : le 23/10, la CI rouge du ticket-544 a arrêté onze tickets alors qu'un seul en dépendait.
**Alternative rejetée** : arrêter toute la file par prudence — un ticket indépendant n'a pas besoin du code manquant.

---

## ADR-063 — Reporter la compression du contexte des agents

**Date** : 2026-10-28
**Portée** : architect
**Décision** : headroom n'entre pas dans le pipeline. Si le sujet rouvre, le point d'entrée est la compression du texte du prompt, pour reviewer et sécurité seulement, avec un garde qui renvoie l'original quand une ligne `FAILED` ou un nom de test disparaît. Le proxy ne s'envisage qu'après un spike sur l'abonnement et le cache. Seuils chiffrés : spec `2026-10-27-compression-contexte-design`, section 4.
**Raison** : le codeur pèse 66 % du coût et n'est atteignable que par le proxy, dont on ignore l'effet sur le cache de prompt et sur le jeton d'abonnement.
**Mesure** : non faite ; estimation 5-10 % du coût, à confirmer (tickets 604, 605).
**Alternative rejetée** : adopter le proxy d'emblée — un gain annoncé par le projet, sans mesure ici, ne justifie pas un composant sur le chemin du jeton.

---

## ADR-066 — Écarter les sous-tâches d'un run

**Date** : 2026-10-30
**Portée** : architect
**Décision** : un run garde un diff, un commit et une revue par tour (ADR-018) : ni sous-tâches tirées du plan, ni écrites dans le ticket. Un ticket trop gros se découpe en tickets. Le ticket-702 journalise l'épuisement des actions. Rouvrir si, sur 30 runs, 10 % des appels du codeur l'épuisent, ou si son tour 1 dépasse 12 min au p90 (8 min aujourd'hui).
**Raison** : le codeur pèse 19 % de la durée d'un ticket ; tests et audit se paient par diff. Des sous-tâches relues ajoutent 3 à 4 min et 47 à 66 % de coût.
**Mesure** : 358 approbations ; 118 tours à tests rouges, 105 refus dont 46 du validateur, qu'une sous-tâche ne voit pas.
**Alternative rejetée** : sous-tâches tirées du plan — son échec est toléré, le run changerait de forme sans le dire.
**Détail** : `docs/superpowers/specs/2026-10-30-sous-taches-dans-un-run-design.md`

---

## ADR-077 — Un outil externe dont on s'inspire s'inscrit au registre et ne se suit jamais en direct

**Date** : 2026-11-05
**Portée** : architect, codeur
**Décision** : aucun outil externe n'est suivi en direct : rien ne s'installe pour se mettre à jour seul. Par défaut on réécrit les idées (`idées réécrites`). Une `copie épinglée` (texte repris tel quel, commit précis, attribution) exige un outil de pur texte, sous licence libre compatible, sans binaire, réseau, télémétrie ni hook, qui tient dans le budget de contexte du rôle. Toute reprise s'inscrit dans `docs/inspirations.md`. Une nouvelle version d'un outil inscrit ouvre un ticket « relire l'écart et reporter ce qui vaut », jamais une mise à jour automatique.
**Raison** : un skill est un texte que le modèle exécute ; un changement en amont modifierait les agents sans revue (ADR-055).
**Alternative rejetée** : laisser les outils se mettre à jour, ou ne rien noter (ticket-715).
**Détail** : ticket-790.

---

## ADR-079 — Une seconde revue par un autre modèle se mesure hors du produit

**Date** : 2026-11-05
**Décision** : un script de `scripts/` rejoue le reviewer actuel et un candidat (Ollama) sur un corpus figé d'avance : diffs corrigés après approbation, diffs sains. Même entrée, sans outils. Règle : ≥ 3 défauts et ≤ 2 faux positifs en plus, adopter ; sinon ≥ 2 défauts en plus sur les diffs de garde, les y réserver ; sinon abandonner. Rejeu qui retrouve moins de 80 % des verdicts d'origine : non concluant. Rien n'entre dans `backend/src`, `agents.json` ni le pipeline avant la conclusion ; l'adoption est une autre ADR.
**Raison** : sur une vingtaine de diffs, un défaut de plus n'est qu'un bruit, sauf corpus et règle figés d'avance.
**Alternative rejetée** : brancher un second reviewer au pipeline — il bloquerait de vrais tickets.
**Détail** : spec `2026-11-05-seconde-revue-design.md`.
