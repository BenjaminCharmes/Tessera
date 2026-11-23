"""Sections à la demande d'un gros fichier de documentation — ticket-1038."""
import json
from pathlib import Path

from tessera.services.documentation.documentation_contenu import BORNE_FICHIER, contenu_et_reduits
from tessera.services.documentation.documentation_sections import message_de_rappel, sections_demandees, texte_des_sections
from tests.test_documentation import PREUVE, _avec_marqueur, _service, _ticket

GROS = (
    "# Archi\n\n## Pipeline\n\nLe pipeline a deux agents.\n\n### Détail\n\nUn détail.\n\n"
    "## Autre\n\nCorps secret de l'autre section.\n\n## Bourrage\n\n" + "x" * BORNE_FICHIER
)


def _projet(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "a.md").write_text(GROS, encoding="utf-8")
    (tmp_path / "docs" / "z.md").write_text("# Petit\n\nTexte court.\n", encoding="utf-8")
    _ticket(tmp_path, "ticket-001")
    _avec_marqueur(tmp_path)


def _demande(fichier: str, titre: str) -> str:
    return json.dumps({"sections": [{"fichier": fichier, "titre": titre}]})


def test_gros_fichier_par_ses_titres_et_petit_fichier_apres_lui_en_entier(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(GROS, encoding="utf-8")
    (tmp_path / "docs" / "z.md").write_text("# Petit\n\nTexte court.\n", encoding="utf-8")

    contenu, reduits = contenu_et_reduits(tmp_path)

    assert "Texte court." in contenu
    assert "## Pipeline" in contenu
    assert "Le pipeline a deux agents." not in contenu
    assert reduits == [f"docs/a.md ({len(GROS)} caractères)"]


def test_sections_demandees_ignore_les_entrees_mal_formees() -> None:
    donnees: dict[str, object] = {"sections": [{"fichier": "docs/a.md", "titre": "## X"}, {"fichier": 3}, "x"]}
    assert sections_demandees(donnees) == [("docs/a.md", "## X")]
    assert sections_demandees({"sections": "non"}) == []
    assert sections_demandees({}) == []


def test_texte_des_sections_va_du_titre_au_titre_de_meme_niveau(tmp_path: Path) -> None:
    _projet(tmp_path)

    texte, ignorees = texte_des_sections(tmp_path, [("docs/a.md", "## Pipeline")])

    assert "Le pipeline a deux agents." in texte
    assert "Un détail." in texte
    assert "Corps secret" not in texte
    assert ignorees == []


def test_texte_des_sections_exclut_hors_docs_dotdot_et_titre_absent(tmp_path: Path) -> None:
    _projet(tmp_path)
    (tmp_path / "src.py").write_text("# Pipeline\nSECRET\n", encoding="utf-8")
    demandes = [
        ("src.py", "# Pipeline"),
        ("docs/../src.py", "# Pipeline"),
        ("docs/a.md", "## Inexistant"),
    ]

    texte, ignorees = texte_des_sections(tmp_path, demandes)

    assert texte == ""
    assert len(ignorees) == 3


def test_texte_des_sections_nomme_le_surplus(tmp_path: Path) -> None:
    _projet(tmp_path)

    texte, ignorees = texte_des_sections(tmp_path, [("docs/a.md", "## Pipeline")], limite=10)

    assert texte == ""
    assert "limite" in ignorees[0]


def test_message_de_rappel_garde_le_message_et_dit_les_demandes_non_servies() -> None:
    message = message_de_rappel("MESSAGE", "\nTEXTE", ["docs/x.md « # Y » ignorée : absente"])
    assert message.startswith("MESSAGE")
    assert "TEXTE" in message
    assert "docs/x.md « # Y » ignorée" in message


async def test_reponse_sections_un_rappel_et_un_ancien_recopie_s_applique(tmp_path: Path) -> None:
    _projet(tmp_path)
    edition = {
        "fichier": "docs/a.md",
        "ancien": "Le pipeline a deux agents.",
        "nouveau": "Le pipeline a six agents.",
        "preuve": PREUVE,
    }
    svc, provider = _service(
        tmp_path, [_demande("docs/a.md", "## Pipeline"), json.dumps({"editions": [edition]})]
    )

    resultat = await svc.mettre_a_jour(tmp_path)

    assert len(provider.appels) == 3  # technique ×2, fonctionnelle ×1
    rappel = str(provider.appels[1]["user"])
    assert "Le pipeline a deux agents." in rappel
    assert "Un détail." in rappel
    assert "Corps secret" not in rappel
    assert "six agents" in (tmp_path / "docs" / "a.md").read_text(encoding="utf-8")
    assert resultat.refus == []


async def test_demandes_invalides_n_entrent_pas_dans_le_rappel(tmp_path: Path) -> None:
    _projet(tmp_path)
    (tmp_path / "secret.py").write_text("MOT_DE_PASSE\n", encoding="utf-8")
    demande = {
        "sections": [
            {"fichier": "secret.py", "titre": "# x"},
            {"fichier": "docs/../secret.py", "titre": "# x"},
            {"fichier": "docs/a.md", "titre": "## Absent"},
        ]
    }
    svc, provider = _service(tmp_path, [json.dumps(demande)])

    await svc.mettre_a_jour(tmp_path)

    rappel = str(provider.appels[1]["user"])
    assert "MOT_DE_PASSE" not in rappel
    assert "Corps secret" not in rappel
    assert "Demandes non servies" in rappel


async def test_sans_gros_fichier_chaque_role_n_est_appele_qu_une_fois(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# Petit\n\n## Pipeline\n\nCourt.\n", encoding="utf-8")
    _ticket(tmp_path, "ticket-001")
    _avec_marqueur(tmp_path)
    svc, provider = _service(tmp_path, [_demande("docs/a.md", "## Pipeline")])

    await svc.mettre_a_jour(tmp_path)

    assert len(provider.appels) == 2
