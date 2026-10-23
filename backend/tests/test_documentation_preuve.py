"""A documentation edit must quote the code that supports it — ticket-542, ADR-057."""
import json
from pathlib import Path

import pytest

from tessera.services.documentation import DocumentationService, EditionRefusee, appliquer_editions
from tessera.services.documentation_code import DiffDeTicket, FichierLivre, MatiereCode
from tessera.services.documentation_preuve import (
    VOLUME_MAX_EDITION,
    VOLUME_MAX_ROLE,
    ControleDePreuve,
    fichiers_de_la_matiere,
    jetons_de,
)
from tests.matiere_factice import matiere_factice


def _matiere(code: str, fichier: str = "") -> MatiereCode:
    """One diff carrying ``code`` and, optionally, one delivered file."""
    diff = DiffDeTicket("ticket-9", f"diff --git a/src/a.py b/src/a.py\n+{code}\n", ["src/a.py"])
    fichiers = [FichierLivre("src/b.py", fichier)] if fichier else []
    return MatiereCode(diffs=[diff], fichiers=fichiers)


def _doc(tmp_path: Path, contenu: str, nom: str = "guide.md") -> Path:
    (tmp_path / "docs").mkdir(exist_ok=True)
    chemin = tmp_path / "docs" / nom
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def _edition(ancien: str, nouveau: str, extrait: str | None, nom: str = "guide.md") -> dict[str, object]:
    edition: dict[str, object] = {"fichier": f"docs/{nom}", "ancien": ancien, "nouveau": nouveau}
    if extrait is not None:
        edition["preuve"] = [{"fichier": "src/a.py", "extrait": extrait}]
    return edition


# ------------------------------------------------------------------
# La preuve
# ------------------------------------------------------------------


@pytest.mark.parametrize("preuve", [None, [], [{"fichier": "src/a.py", "extrait": "  "}]])
def test_an_edition_without_usable_proof_is_refused(tmp_path: Path, preuve: object) -> None:
    fichier = _doc(tmp_path, "Avant.\n")
    edition: dict[str, object] = {"fichier": "docs/guide.md", "ancien": "Avant.", "nouveau": "Après."}
    if preuve is not None:
        edition["preuve"] = preuve

    with pytest.raises(EditionRefusee, match="preuve"):
        appliquer_editions(tmp_path, [edition], matiere=_matiere("x = 1"))

    assert fichier.read_text(encoding="utf-8") == "Avant.\n"


def test_a_removal_needs_no_proof(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "# Guide\n\nGarde.\n\nÀ retirer.\n")

    appliquer_editions(
        tmp_path, [{"fichier": "docs/guide.md", "ancien": "\nÀ retirer.\n", "nouveau": ""}],
        matiere=_matiere("x = 1"),
    )

    assert "À retirer" not in fichier.read_text(encoding="utf-8")


def test_an_extract_absent_from_the_material_is_refused(tmp_path: Path) -> None:
    _doc(tmp_path, "Avant.\n")

    with pytest.raises(EditionRefusee, match="preuve.*n'est ni dans"):
        appliquer_editions(
            tmp_path, [_edition("Avant.", "Après.", "def inconnue()")],
            matiere=_matiere("def connue()"),
        )


def test_an_extract_from_a_delivered_file_is_accepted(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "Avant.\n")

    appliquer_editions(
        tmp_path, [_edition("Avant.", "Après.", "SEUIL = 3")],
        matiere=_matiere("autre", fichier="SEUIL = 3\n"),
    )

    assert "Après." in fichier.read_text(encoding="utf-8")


def test_the_extract_comparison_tolerates_typography(tmp_path: Path) -> None:
    # Le diff porte une apostrophe typographique et une espace insécable ; l'agent
    # recopie avec une apostrophe droite et une espace normale.
    fichier = _doc(tmp_path, "Avant.\n")
    matiere = _matiere("message = \"l’état du lot est prêt\"")

    appliquer_editions(
        tmp_path, [_edition("Avant.", "Après.", "l'état du lot est prêt")], matiere=matiere,
    )

    assert "Après." in fichier.read_text(encoding="utf-8")


# ------------------------------------------------------------------
# Les jetons vérifiables : une famille par test
# ------------------------------------------------------------------

#: (matière, texte qui s'y trouve, texte qui n'y est pas)
FAMILLES = {
    "adr": ("ADR-018 pose la règle", "Voir ADR-018.", "Voir ADR-019."),
    "ticket": ("fix du ticket-12", "Livré par le ticket-12.", "Livré par le ticket-13."),
    "nombre": ("limite de 5 Mo par image", "Jusqu'à 5 Mo.", "Jusqu'à 10 Mo."),
    "migration": ("0012_groupes.py", "La migration 0012 crée les groupes.", "La migration 0021 crée les groupes."),
    "extension": ("formats = GIF, PNG", "Les images GIF passent.", "Les images AVIF passent."),
    "guillemets": ("bouton Annuler", "Clique sur « Annuler ».", "Clique sur « Supprimer »."),
}


@pytest.mark.parametrize("famille", sorted(FAMILLES))
def test_a_token_absent_from_the_material_is_refused(tmp_path: Path, famille: str) -> None:
    code, _, faux = FAMILLES[famille]
    fichier = _doc(tmp_path, "Avant.\n")

    with pytest.raises(EditionRefusee, match="jeton vérifiable"):
        appliquer_editions(tmp_path, [_edition("Avant.", faux, code)], matiere=_matiere(code))

    assert fichier.read_text(encoding="utf-8") == "Avant.\n"


@pytest.mark.parametrize("famille", sorted(FAMILLES))
def test_a_token_found_in_the_material_is_accepted(tmp_path: Path, famille: str) -> None:
    code, vrai, _ = FAMILLES[famille]
    fichier = _doc(tmp_path, "Avant.\n")

    appliquer_editions(tmp_path, [_edition("Avant.", vrai, code)], matiere=_matiere(code))

    assert vrai in fichier.read_text(encoding="utf-8")


def test_an_adr_number_next_to_another_one_in_the_material_is_refused(tmp_path: Path) -> None:
    # Le cas de Kadoomi : la matière porte ADR-018, l'agent écrit ADR-019.
    _doc(tmp_path, "Groupes.\n")

    with pytest.raises(EditionRefusee, match="ADR-19"):
        appliquer_editions(
            tmp_path,
            [_edition("Groupes.", "Les groupes relèvent d'ADR-019.", "ADR-018")],
            matiere=_matiere("# voir ADR-018"),
        )


def test_a_token_already_in_the_replaced_text_is_not_new(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "La limite est de 10 Mo.\n")

    appliquer_editions(
        tmp_path, [_edition("La limite est de 10 Mo.", "La limite est de 10 Mo par image.", "x = 1")],
        matiere=_matiere("x = 1"),
    )

    assert "par image" in fichier.read_text(encoding="utf-8")


def test_a_token_found_only_in_the_current_documentation_is_refused(tmp_path: Path) -> None:
    # La documentation actuelle porte les erreurs à corriger : elle n'est pas une source.
    _doc(tmp_path, "Avant.\n", "guide.md")
    _doc(tmp_path, "Limite de 10 Mo (ADR-099).\n", "autre.md")

    with pytest.raises(EditionRefusee, match="jeton vérifiable"):
        appliquer_editions(
            tmp_path, [_edition("Avant.", "Limite de 10 Mo.", "x = 1")], matiere=_matiere("x = 1"),
        )


def test_a_token_quoted_by_a_ticket_is_accepted(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "Avant.\n")

    appliquer_editions(
        tmp_path, [_edition("Avant.", "Règle ADR-031.", "x = 1")],
        matiere=_matiere("x = 1"), tickets="Le ticket applique ADR-031.",
    )

    assert "ADR-031" in fichier.read_text(encoding="utf-8")


def test_tokens_of_every_family_are_extracted() -> None:
    texte = 'ADR-5, ticket-7, 3,5 Mo, migration 0012, AVIF, « Valider »'

    familles = {famille for famille, _ in jetons_de(texte)}

    assert familles == {"adr", "ticket", "nombre", "migration", "extension", "guillemets"}


# ------------------------------------------------------------------
# Le volume
# ------------------------------------------------------------------


def test_one_edition_replacing_more_than_the_cap_is_refused(tmp_path: Path) -> None:
    ancien = "a" * (VOLUME_MAX_EDITION + 1)
    fichier = _doc(tmp_path, ancien + "z" * 10_000)

    with pytest.raises(EditionRefusee, match="volume"):
        appliquer_editions(tmp_path, [_edition(ancien, "b", "x = 1")], matiere=_matiere("x = 1"))

    assert fichier.read_text(encoding="utf-8").startswith("aaa")


def test_one_edition_at_the_cap_is_accepted(tmp_path: Path) -> None:
    ancien = "a" * VOLUME_MAX_EDITION
    fichier = _doc(tmp_path, ancien + "z" * 10_000)

    appliquer_editions(tmp_path, [_edition(ancien, "b", "x = 1")], matiere=_matiere("x = 1"))

    assert fichier.read_text(encoding="utf-8").startswith("b")


def test_a_role_cannot_replace_more_than_the_cap_over_a_batch(tmp_path: Path) -> None:
    taille = VOLUME_MAX_EDITION - 300
    blocs = ["abcde"[i] * taille for i in range(5)]
    assert taille * 5 > VOLUME_MAX_ROLE >= taille * 4
    _doc(tmp_path, "\n".join(blocs) + "z" * 30_000)
    editions = [_edition(bloc, "x", "x = 1") for bloc in blocs]

    with pytest.raises(EditionRefusee, match="volume"):
        appliquer_editions(tmp_path, editions, matiere=_matiere("x = 1"))


def test_a_creation_is_exempt_from_volume_but_not_from_proof(tmp_path: Path) -> None:
    gros = "# Guide\n\n" + "texte " * 1000
    creation: dict[str, object] = {"fichier": "docs/neuf.md", "contenu": gros}

    with pytest.raises(EditionRefusee, match="preuve"):
        appliquer_editions(tmp_path, [creation], matiere=_matiere("x = 1"))

    creation["preuve"] = [{"fichier": "src/a.py", "extrait": "x = 1"}]
    appliquer_editions(tmp_path, [creation], matiere=_matiere("x = 1"))

    assert (tmp_path / "docs" / "neuf.md").read_text(encoding="utf-8") == gros


def test_the_control_without_material_checks_nothing(tmp_path: Path) -> None:
    fichier = _doc(tmp_path, "Avant.\n")

    appliquer_editions(tmp_path, [_edition("Avant.", "10 Mo", None)])

    assert "10 Mo" in fichier.read_text(encoding="utf-8")


def test_files_of_the_material_are_listed_once_and_sorted() -> None:
    matiere = MatiereCode(
        diffs=[DiffDeTicket("t", "", ["src/b.py", "src/a.py"])],
        fichiers=[FichierLivre("src/a.py", "x")],
        fichiers_non_montres=["src/c.py"],
    )

    assert fichiers_de_la_matiere(matiere) == ["src/a.py", "src/b.py", "src/c.py"]


def test_the_volume_is_counted_per_control_instance() -> None:
    controle = ControleDePreuve(_matiere("x = 1"))
    edition = _edition("a" * VOLUME_MAX_EDITION, "b", "x = 1")

    for _ in range(VOLUME_MAX_ROLE // VOLUME_MAX_EDITION):
        controle.verifier(edition, "docs/guide.md")

    with pytest.raises(EditionRefusee, match="volume"):
        controle.verifier(edition, "docs/guide.md")


# ------------------------------------------------------------------
# Le cas du 22/10 : un ticket d'en-têtes de sécurité réécrit « Gérer ton compte »
# ------------------------------------------------------------------

EN_TETES = 'response.headers["X-Frame-Options"] = "DENY"\nresponse.headers["Referrer-Policy"] = "no-referrer"'
GUIDE = "# Guide\n\n## Gérer ton compte\n\n" + "Tu modifies ton profil depuis les réglages. " * 60


def test_a_security_headers_diff_cannot_support_a_rewrite_of_the_account_section(
    tmp_path: Path,
) -> None:
    fichier = _doc(tmp_path, GUIDE)
    ancien = GUIDE.split("\n\n", 2)[2].strip()

    # Un extrait qui soutiendrait la réécriture du compte n'existe pas dans le diff.
    with pytest.raises(EditionRefusee, match="preuve"):
        appliquer_editions(
            tmp_path,
            [_edition(ancien[:300], "Tu supprimes ton compte depuis les réglages.", "def supprimer_compte(")],
            matiere=_matiere(EN_TETES),
        )
    # Citer un extrait réel mais étranger au passage ne contourne pas le plafond :
    # réécrire toute la section dépasse ce qu'une édition peut remplacer.
    with pytest.raises(EditionRefusee, match="volume"):
        appliquer_editions(
            tmp_path,
            [_edition(ancien, "Tu gères ton compte autrement.", 'response.headers["X-Frame-Options"] = "DENY"')],
            matiere=_matiere(EN_TETES),
        )

    assert fichier.read_text(encoding="utf-8") == GUIDE


# ------------------------------------------------------------------
# Le service : tour de correction et contrôle branché
# ------------------------------------------------------------------


class _Provider:
    def __init__(self, reponses: list[str]) -> None:
        self.reponses = list(reponses)
        self.appels: list[dict[str, object]] = []

    async def complete(self, **kwargs: object) -> object:
        self.appels.append(kwargs)

        class _R:
            content = self.reponses.pop(0) if self.reponses else '{"editions": []}'
            input_tokens = output_tokens = cache_read_tokens = 0
            cost_usd = 0.0

        return _R()


def _service(tmp_path: Path, reponses: list[str]) -> tuple[DocumentationService, _Provider]:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text(f"prompt {role}", encoding="utf-8")
    (tmp_path / "tickets" / "done").mkdir(parents=True)
    (tmp_path / "tickets" / "done" / "ticket-001-x.md").write_text(
        '---\nid: ticket-001\ntitle: "T"\n---\n\nRespecte ADR-031.\n', encoding="utf-8"
    )
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "documentation.json").write_text('{"documentes": []}', encoding="utf-8")
    provider = _Provider(reponses)
    service = DocumentationService(provider, prompts, matiere=matiere_factice())  # type: ignore[arg-type]
    return service, provider


async def test_the_corrective_round_gets_the_rule_and_the_files_of_the_material(
    tmp_path: Path,
) -> None:
    _doc(tmp_path, "Avant.\n")
    sans_preuve = json.dumps({"editions": [_edition("Avant.", "Après.", None)]})
    avec_preuve = json.dumps({"editions": [_edition("Avant.", "Après.", "code de ticket-001")]})
    service, provider = _service(tmp_path, [sans_preuve, avec_preuve, '{"editions": []}'])

    resultat = await service.mettre_a_jour(tmp_path)

    correction = str(provider.appels[1]["user"])
    assert "règle « preuve »" in correction
    assert "src/ticket-001.py" in correction
    assert resultat.tour_de_correction is True
    assert not resultat.refus
    assert "Après." in (tmp_path / "docs" / "guide.md").read_text(encoding="utf-8")


async def test_the_service_checks_tokens_against_the_tickets_it_gave_the_agent(
    tmp_path: Path,
) -> None:
    _doc(tmp_path, "Avant.\n")
    ok = json.dumps({"editions": [_edition("Avant.", "Règle ADR-031.", "code de ticket-001")]})
    service, _ = _service(tmp_path, [ok, '{"editions": []}'])

    resultat = await service.mettre_a_jour(tmp_path)

    assert not resultat.refus
    assert "ADR-031" in (tmp_path / "docs" / "guide.md").read_text(encoding="utf-8")


async def test_the_service_refuses_an_invented_token_twice(tmp_path: Path) -> None:
    _doc(tmp_path, "Avant.\n")
    faux = json.dumps({"editions": [_edition("Avant.", "Règle ADR-099.", "code de ticket-001")]})
    service, _ = _service(tmp_path, [faux, faux, '{"editions": []}'])

    resultat = await service.mettre_a_jour(tmp_path)

    assert any("jeton vérifiable" in r for r in resultat.refus)
    assert (tmp_path / "docs" / "guide.md").read_text(encoding="utf-8") == "Avant.\n"
