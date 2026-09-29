---
id: ticket-206
title: "Implanter le contrôle des termes interdits au push"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-206 — Implanter le contrôle des termes interdits au push

## Objectif

Implémenter `TermesInterditsService` (ADR-048) et le brancher dans
`GitHubWorkflowService.open_pull_request()` pour que tout push soit refusé
si les termes de `FORBIDDEN_TERMS` y apparaissent.

## Contexte

ADR-048 décide où le contrôle s'exerce (au push, pas au commit), ce qu'il
vérifie (lignes ajoutées, messages, auteurs), comment un projet s'en exempte
(`"confidentiality": "professional"` dans `agents.json`), et ce que la
sortie dit (localisation sans le terme).

L'interface est dans `backend/src/tessera/services/termes_interdits.py`.
`PolitiqueRun` devra porter un champ `confidentialite: str | None` lu depuis
`agents.json`.

## Ce qu'il faut faire

### 1. `TermesInterditsService`

- Charge `FORBIDDEN_TERMS` depuis `os.environ` (virgules comme séparateurs)
- Normalise chaque terme : minuscules, accents supprimés (NFKD + filtre
  catégorie), séparateurs (`-`, `_`, `.`) traités comme espaces
- La même normalisation s'applique au texte inspecté
- Correspondance sur **mots entiers** uniquement (`\b` ou équivalent
  après normalisation)
- `actif` : `False` quand la liste est vide ou absente

### 2. `verifier(lignes_ajoutees, messages_commit, auteurs)`

- `lignes_ajoutees` : lignes commençant par `+` dans le diff (hors `+++`)
- `messages_commit` : messages en clair
- `auteurs` : chaînes `"Prénom Nom <email>"` de chaque commit
- Rend une liste de `ViolationTerme(source=...)` :
  - `"file:<chemin>"` si un fichier est en cause (extraire le chemin depuis
    la ligne `+++ b/<chemin>` du diff)
  - `"commit:<sha7>"` pour un message ou un auteur
- S'arrête au premier terme trouvé dans chaque source (pas de liste
  exhaustive de tous les termes violés — inutile, et un log se partage)

### 3. `PolitiqueRun`

- Ajouter `confidentialite: str | None = None` lu par `_lire_chaine(project_path, "confidentiality")`
- Propriété `exempte_controle_termes: bool` : `True` ssi `confidentialite == "professional"`

### 4. Intégration dans `GitHubWorkflowService`

- Ajouter `termes: TermesInterditsChecker | None = None` au constructeur
- Dans `open_pull_request()`, avant `push_branch()` :
  - Si le service est inactif ou que `politique.exempte_controle_termes` :
    aucun contrôle
  - Sinon : récupérer le diff (`current_diff()`), extraire les lignes
    ajoutées ; récupérer messages et auteurs via une méthode nouvelle de
    `_GitWorkspace` : `commits_depuis_base(base, branch) -> list[CommitInfo]`
  - Lever `WorkflowError` avec les sources en clair si violations
- Le `LivraisonService` n'a pas à changer : il reçoit déjà `WorkflowError`
  comme `Livraison.arret`

### 5. `GitWorkspaceService`

Ajouter :
```python
async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
    """SHA court, message et auteur de chaque commit entre base et branch."""
```

`CommitInfo` : dataclass `(sha7: str, message: str, auteur: str)`.

## Critères d'acceptation

- [ ] `TermesInterditsService.verifier()` passe les cas : terme en majuscules,
      terme accentué, terme avec tiret, correspondance sous-chaîne (doit
      **ne pas** déclencher), liste vide (doit ne pas déclencher)
- [ ] Un push avec un terme dans une ligne ajoutée lève `WorkflowError` dont le
      message contient `"file:"` mais pas le terme lui-même
- [ ] Un push avec un terme dans un message de commit lève `WorkflowError`
      contenant `"commit:<sha7>"`
- [ ] `"confidentiality": "professional"` dans `agents.json` court-circuite le
      contrôle (aucune `WorkflowError` levée)
- [ ] Liste `FORBIDDEN_TERMS` absente : aucun contrôle, pas d'exception
- [ ] `PolitiqueRun.lire()` lit `confidentialite` sans casser les projets
      existants (champ absent → `None`)
- [ ] Le paramètre `termes` de `GitHubWorkflowService` est optionnel : les appels existants qui ne le fournissent pas restent valides

## Ce que ça ne fait pas

- Pas de hook pre-push pour les commits manuels hors IDE (ticket-207)
- Pas de vérification des fichiers binaires (les lignes `+` d'un diff binaire
  sont illisibles, et un binaire ne contient pas de nom en clair exploitable)
- Pas d'inventaire exhaustif de tous les termes violés : une source suffit
  pour décider de bloquer

## Dépendances

ADR-048, ticket-204 (design)
