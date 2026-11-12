"""CI checkouts do not leave the GitHub token to the PR code — ticket-945."""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def test_every_ci_checkout_disables_persisted_credentials() -> None:
    """Each actions/checkout step of ci.yml sets persist-credentials: false."""
    texte = (RACINE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    etapes = re.findall(r"- uses: actions/checkout@[^\n]*\n((?:[ ]+[^-\s][^\n]*\n)*)", texte)
    assert etapes, "aucun actions/checkout trouvé dans ci.yml"
    for bloc in etapes:
        assert "persist-credentials: false" in bloc, bloc
