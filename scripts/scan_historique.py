"""Scan de tout ce que la publication du dépôt exposerait, sans jamais afficher un terme — ticket-230.

À lancer avant de rendre un dépôt public, ou après un incident :
`python scripts/scan_historique.py` depuis la racine du dépôt.

Lit FORBIDDEN_TERMS dans le .env du dépôt. N'affiche que des emplacements
(blob et chemins, commit, ref, PR/issue et champ) et un nombre de termes.

Couvre :
- chaque blob joignable depuis toutes les refs, y compris refs/pull/*/head
- messages de commit, auteurs et committers (noms et adresses)
- noms de branches et de tags
- titres, corps et commentaires des PR et issues, commentaires de revue, releases
"""
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           check=True).stdout.strip())
GH_REPO = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                         capture_output=True, text=True, cwd=REPO).stdout.strip()


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, check=True).stdout


def termes() -> list[str]:
    import os
    if os.environ.get("FORBIDDEN_TERMS"):
        return [t.strip() for t in os.environ["FORBIDDEN_TERMS"].split(",") if t.strip()]
    txt = (REPO / ".env").read_text(encoding="utf-8")
    m = re.search(r"^FORBIDDEN_TERMS=(.*)$", txt, re.M)
    if not m:
        sys.exit("FORBIDDEN_TERMS absent de .env : rien à scanner.")
    return [t.strip() for t in m.group(1).strip().strip("'\"").split(",") if t.strip()]


def normaliser(texte: str) -> str:
    return unicodedata.normalize("NFD", texte).encode("ascii", "ignore").decode().lower()


def motif(terme: str) -> re.Pattern[str]:
    lettres = re.sub(r"[\s\-_.]+", "", normaliser(terme))
    corps = r"[\s\-_.]*".join(re.escape(c) for c in lettres)
    return re.compile(rf"(?<![a-z0-9]){corps}(?![a-z0-9])")


MOTIFS: list[re.Pattern[str]] = []
TROUVES: dict[str, set[int]] = defaultdict(set)  # emplacement -> index des termes


def examiner(emplacement: str, texte: str) -> None:
    h = normaliser(texte)
    for i, m in enumerate(MOTIFS):
        if m.search(h):
            TROUVES[emplacement].add(i)


def main() -> None:
    MOTIFS.extend(motif(t) for t in termes())
    print(f"{len(MOTIFS)} terme(s) chargé(s).")

    # Les PR gardent leurs commits sous refs/pull/N/head, même effacés ailleurs.
    subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin",
                    "+refs/pull/*/head:refs/remotes/pr/*"], capture_output=True)

    # 1. Blobs de toutes les refs, dédupliqués, avec leurs chemins.
    chemins: dict[str, set[str]] = defaultdict(set)
    for ligne in git("rev-list", "--all", "--objects").decode("utf-8", "replace").splitlines():
        sha, _, chemin = ligne.partition(" ")
        if chemin:
            chemins[sha].add(chemin)
    types = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)", "--batch-all-objects")
    blobs = [l.split()[0] for l in types.decode().splitlines() if l.split()[1] == "blob" and l.split()[0] in chemins]
    print(f"{len(blobs)} blob(s) joignables.")
    for sha in blobs:
        contenu = git("cat-file", "-p", sha)
        if b"\0" in contenu[:8000]:
            continue  # binaire
        examiner(f"blob {sha[:10]} ({', '.join(sorted(chemins[sha]))[:120]})", contenu.decode("utf-8", "replace"))

    # 2. Métadonnées de commit.
    sep = "\x1e"
    sortie = git("log", "--all", f"--format=%H{sep}%an <%ae>{sep}%cn <%ce>{sep}%B\x1f").decode("utf-8", "replace")
    for bloc in sortie.split("\x1f"):
        if not bloc.strip():
            continue
        sha, auteur, committer, message = (bloc.strip("\n").split(sep) + ["", "", ""])[:4]
        examiner(f"commit {sha[:10]} auteur", auteur)
        examiner(f"commit {sha[:10]} committer", committer)
        examiner(f"commit {sha[:10]} message", message)

    # 3. Noms de refs.
    for ref in git("for-each-ref", "--format=%(refname)").decode().splitlines():
        examiner(f"ref {ref}", ref)

    # 4. Métadonnées GitHub.
    def api(chemin: str) -> list[dict]:
        r = subprocess.run(["gh", "api", "--paginate", chemin], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"  (gh api {chemin} : échec, non couvert)")
            return []
        return json.loads(r.stdout.replace("][", ","))

    for pr in api(f"repos/{GH_REPO}/pulls?state=all&per_page=100"):
        examiner(f"PR #{pr['number']} titre", pr.get("title") or "")
        examiner(f"PR #{pr['number']} corps", pr.get("body") or "")
        examiner(f"PR #{pr['number']} branche", pr["head"]["ref"])
    for iss in api(f"repos/{GH_REPO}/issues?state=all&per_page=100"):
        if "pull_request" not in iss:
            examiner(f"issue #{iss['number']} titre", iss.get("title") or "")
            examiner(f"issue #{iss['number']} corps", iss.get("body") or "")
    for c in api(f"repos/{GH_REPO}/issues/comments?per_page=100"):
        examiner(f"commentaire {c['html_url'].rsplit('/', 1)[-1]} ({c['issue_url'].rsplit('/', 1)[-1]})", c.get("body") or "")
    for c in api(f"repos/{GH_REPO}/pulls/comments?per_page=100"):
        examiner(f"commentaire de revue {c['id']} (PR {c['pull_request_url'].rsplit('/', 1)[-1]})", c.get("body") or "")
    for rel in api(f"repos/{GH_REPO}/releases?per_page=100"):
        examiner(f"release {rel.get('tag_name')}", f"{rel.get('name') or ''}\n{rel.get('body') or ''}")

    print()
    if not TROUVES:
        print("AUCUN terme trouvé.")
        return
    print(f"{len(TROUVES)} emplacement(s) avec au moins un terme :")
    for emplacement, idx in sorted(TROUVES.items()):
        print(f"  {emplacement} — {len(idx)} terme(s) distinct(s)")


if __name__ == "__main__":
    main()
