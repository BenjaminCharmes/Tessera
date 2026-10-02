# Audit des ADR — état au 2026-10-02

Classement : **règle** (contrainte active), **histoire** (choix passé, ne
contraint plus le comportement), **obsolète** (remplacé, ADR cité),
**fusion** (règle absorbée dans un autre ADR, cité).

| ADR | Titre | Classement | Justification |
|-----|-------|-----------|---------------|
| 001 | Self-hosting comme premier projet | histoire | Principe fondateur ; aucun agent n'a à décider où construire l'IDE. |
| 002 | Pas de framework agent externe | histoire | Choix de stack encodé dans CLAUDE.md ; aucun agent ne choisit l'implémentation. |
| 003 | Tickets comme fichiers Markdown | histoire | Format établi, inscrit dans la pratique ; aucun agent n'a à le décider. |
| 004 | Tauri plutôt qu'Electron | histoire | Stack desktop fixée ; aucun agent n'a à choisir. |
| 005 | uv comme gestionnaire Python | histoire | Règle couverte par CLAUDE.md global ; portée architect confirme le choix passé. |
| 006 | ProjectLoader filtre sur CLAUDE.md | règle | Le codeur qui touche ProjectLoader doit respecter ce contrat. |
| 007 | name parsé depuis le H1 du CLAUDE.md | règle | Le codeur qui touche Project doit extraire name depuis le H1. |
| 008 | Orchestrateur stateless | règle | L'orchestrateur doit rester stateless à chaque requête. |
| 009 | Verdict reviewer parsé par mot-clé | règle | Le reviewer doit répondre APPROVED ou CHANGES_REQUESTED en début de ligne. |
| 010 | github-sync intégré dans POST /agents/run | règle | Pas d'endpoint dédié pour github-sync. |
| 011 | httpx plutôt que PyGitHub | histoire | Choix de librairie fait, encodé dans le code existant ; portée architect. |
| 012 | Monaco bundlé localement | règle | Monaco ne doit pas être chargé depuis un CDN. |
| 013 | Hooks React sans gestionnaire d'état global | règle | Pas de Zustand/Jotai tant que l'état tient dans useActiveProject. |
| 014 | Vitest + RTL pour les tests frontend | règle | Vitest et RTL sont les frameworks de test obligatoires. |
| 015 | CI : jobs parallèles, macOS conditionnel | histoire | Structure CI définie dans le code ; portée architect confirme le choix passé. |
| 016 | Scope filesystem Tauri : $HOME pour la v0 | obsolète | Remplacé par ADR-040 : Tauri n'expose plus aucune permission fs:*. |
| 017 | Abstraction LLMProvider | règle | Les services passent par LLMProvider, jamais le SDK directement. |
| 018 | Une branche et un commit par run | règle | Chaque run sur sa branche, commit à chaque sortie, arbre toujours propre. |
| 019 | Le chat de l'IDE commite comme un run | règle | Le chat ne laisse jamais l'arbre sale. |
| 020 | Deux plafonds distincts : dépense et quota | règle | Le run autonome vérifie budget et quota entre chaque ticket. |
| 021 | Artefacts via .git/info/exclude | règle | Les artefacts locaux s'excluent via exclude, jamais via .gitignore. |
| 022 | L'agent de workflow pousse et ouvre la PR | règle | Le push n'est jamais forcé. |
| 023 | Mode artefacts échoue fermé | règle | local est le défaut en l'absence de déclaration dans agents.json. |
| 024 | Projet = racine de son propre dépôt | règle | La racine git est vérifiée avant toute création de branche. |
| 025 | Question sans réponse → hypothèse énoncée | règle | Timeout → reprendre en énonçant l'hypothèse retenue. |
| 026 | Cinq familles de couleurs, une par rôle | règle | Palette UI à respecter ; un test verrouille la règle. |
| 027 | Agents ne touchent pas à l'historique git | règle | Le hook PreToolUse bloque git et gh en écriture. |
| 028 | Travailler dans le dépôt parent se déclare | règle | git_root: ancestor est la seule valeur qui lève la protection de ADR-024. |
| 029 | Jusqu'où l'agent va se déclare par projet | règle | autonomy: commit/pr/merge dans agents.json (défaut : commit). |
| 030 | Livraison étape à part, ne fait pas échouer le run | règle | Un run non approuvé ne se livre jamais ; amendé par ADR-051. |
| 031 | Agent n'écrit que sous la racine de son projet | règle | Le hook PreToolUse bloque toute écriture hors du dossier du projet. |
| 032 | Un ADR déclare qui il contraint | histoire | Choix d'implémentation d'adr.py ; portée architect confirme. |
| 033 | Un conflit se tente, et se relit toujours | règle | resolveur-conflit tente, mais une résolution de conflit ne se merge jamais seule. |
| 034 | Une règle n'est décrite qu'à un endroit | histoire | Méta-règle vérifiée par test_consignes_coherentes.py ; portée architect. |
| 035 | Documentation par lot, en modifications ciblées | histoire | Workflow encodé dans les prompts des agents doc ; portée architect. |
| 036 | Clef de manifeste rétrocompatible | histoire | Migration faite, vibe_artifacts reste lue ; portée architect. |
| 037 | Panne de production → blocked + commit | règle | Toute exception en production → run blocked, pas d'erreur serveur. |
| 038 | Un projet ne porte qu'un run à la fois | règle | RunLock en mémoire refuse le second run (409). |
| 039 | Porte du pipeline qui n'a pas pu juger refuse | règle | Audit et validation échouent fermés sur panne ou réponse illisible. |
| 040 | Shell desktop sans porte vers le disque | règle | Tauri sans fs:/shell:*, contrôle dans routers/fs.py. |
| 041 | Un run est observé, pas possédé | règle | Architecture POST /orchestrator/run + WS /orchestrator/observe. |
| 042 | Services déclarés dans agents.json | règle | Aucune détection automatique de commandes de démarrage. |
| 043 | Rien de professionnel dans un dépôt personnel | règle | Aucune donnée pro dans le contenu ni les métadonnées git. |
| 044 | Ce qu'une machine lit s'écrit en anglais | règle | Identifiants, commits, docstrings en anglais ; ADR et tickets en français. |
| 045 | Dépôt sans CI merge sur le verdict du pipeline | règle | merge_without_ci: true dans agents.json pour les dépôts sans CI. |
| 046 | Le provider se déclare par rôle | règle | provider + model + fallback dans agents.json, via provider_pour_role. |
| 047 | Les graphiques ont leur palette | règle | data-1/2/3 dans design/charts/ uniquement, jamais en brut. |
| 048 | Vérifier les termes interdits avant tout push | règle | Le pipeline vérifie diff, commits et auteurs contre FORBIDDEN_TERMS. |
| 049 | Un rôle qui lit le web n'a pas de shell | règle | web: true → WebFetch + WebSearch, pas Bash. |
| 050 | Termes interdits arrêtés à trois portes | règle | Push pipeline + hook pre-push + CI ; une porte absente refuse. |
| 051 | Libérer l'arbre après la PR, pas après le merge | règle | Phase 1 libère le verrou ; CIWatcher gère CI et merge en fond. |
