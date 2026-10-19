---
agent: codeur
created: 2026-10-19
depends_on:
- ticket-521
- ticket-522
estimated_days: 0.75
id: ticket-523
pr_number: 583
priority: medium
status: done
title: A worktree is populated from its declared entries and its links are removed
  before anything else
type: feat
---

# ticket-523 — Peupler un worktree, et retirer ses liens d'abord

## Objectif
Copier et lier dans un worktree neuf ce que `worktree.populate` déclare, et en
faire la suppression sans jamais traverser un lien. C'est la correction directe
de l'accident du 14/10 : une jonction `node_modules` a vidé le `node_modules`
du dépôt.

## Contexte
ADR-056, spec § 2. Le hook d'écriture (ADR-031) résout les liens des deux
côtés : une écriture à travers un lien sort de la racine, donc se refuse. Un
lien est en lecture seule pour les outils fichier ; c'est voulu.

## Ce qu'il faut faire
Dans `services/run_worktree_populate.py` (le ticket-522 tient `run_worktree.py`
sous 200 lignes ; `supprimer` importe `retirer_les_liens` d'ici) :

```python
async def peupler(wt: RunWorktree, depot: Path, config: ConfigWorktree) -> list[str]: ...
    # renvoie les chemins absents, déjà journalisés
def retirer_les_liens(racine: Path) -> list[Path]: ...
```

- `copy` : copie du fichier ou du dossier depuis le checkout (`depot`), vers
  le même chemin relatif du worktree.
- `link` : jonction sous Windows (`_winapi.CreateJunction`, aucun privilège),
  lien symbolique ailleurs. Refusé et journalisé si le chemin n'est **pas**
  ignoré par git (`git check-ignore -q`) : un lien ne vise jamais du suivi.
- Entrée absente dans le checkout : journal `worktree_populate_manquant` avec
  le chemin, pas d'exception.
- `retirer_les_liens` retire chaque jonction (`os.rmdir`) ou lien (`os.unlink`)
  du worktree, détectés par l'attribut de point d'analyse sous Windows
  (`st_file_attributes`, Python 3.11 : pas d'`os.path.isjunction`). Elle ne
  parcourt **jamais** l'intérieur d'un lien.
- `supprimer` (ticket-522) l'appelle **avant** tout `worktree remove` et tout
  `rmtree`. Si un lien subsiste après, `supprimer` s'arrête sans rien effacer.

## Tests
`backend/tests/test_run_worktree_populate.py` :
- [ ] `copy` d'un fichier et d'un dossier : contenu identique, modification dans le worktree absente du checkout
- [ ] `link` : le chemin du worktree montre le contenu du checkout
- [ ] **la suppression d'un worktree dont `node_modules` est un lien laisse intact le `node_modules` du checkout** (le fichier témoin y est encore)
- [ ] `link` sur un chemin suivi par git → refusé, journalisé, rien créé
- [ ] entrée absente → journalisée, `peupler` la renvoie, les autres entrées sont peuplées
- [ ] `retirer_les_liens` ne descend pas dans la cible (compteur d'accès ou fichier témoin)
- [ ] un lien qui ne se laisse pas retirer arrête `supprimer` : le worktree reste
- [ ] `backend/tests/test_perimetre_ecriture.py`, cas ajouté : une écriture `Write` à travers un lien est refusée par le hook de périmètre

## Critères d'acceptation
- [ ] Les huit tests ci-dessus existent et passent
- [ ] Un test vérifie, avec des doubles qui notent l'ordre des appels, que chaque fonction de suppression du module appelle `retirer_les_liens` avant `rmtree` ou `worktree remove`
- [ ] Le `.env` de Tessera ne peut être ni copié ni lié (déjà filtré par le ticket-521 ; un test de bout en bout le confirme)

## Dépendances
Tickets 521 et 522.

## Ce que ça ne fait pas
Ni branchement dans le run (519), ni reprise des orphelins (520).