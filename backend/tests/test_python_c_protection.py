"""Un `python -c` qui écrit un fichier protégé est refusé — ticket-326."""
from pathlib import Path

import pytest

from tessera.services.providers.chemins_proteges import INTERPRETE_PROTEGE_REFUS
from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.redirections_bash import cibles_interpreteur_ecriture


def _projet(tmp_path: Path, nom: str = "client") -> Path:
    racine = tmp_path / "projects" / nom
    racine.mkdir(parents=True, exist_ok=True)
    return racine


# ------------------------------------------------------------------
# Détection bas niveau — cibles_interpreteur_ecriture
# ------------------------------------------------------------------


def test_python_c_open_write_claude_md_detecte() -> None:
    """python -c "open('CLAUDE.md','w').write(...)" est détecté."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"open('CLAUDE.md','w').write('x')\""
    )
    assert "CLAUDE.md" in resultat


def test_python_c_lecture_seule_non_detecte() -> None:
    """python -c qui lit un fichier protégé sans l'écrire n'est pas détecté."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"print(open('CLAUDE.md').read())\""
    )
    assert resultat == []


def test_python_m_pytest_non_detecte() -> None:
    """python -m pytest n'a pas de -c : pas de détection."""
    assert cibles_interpreteur_ecriture("python -m pytest -q") == []


def test_python3_c_agents_json_ecriture_detecte() -> None:
    """python3 -c avec agents.json en mode 'w' est détecté."""
    resultat = cibles_interpreteur_ecriture(
        "python3 -c \"open('agents.json','w').write('{}')\""
    )
    assert "agents.json" in resultat


def test_python_c_git_write_text_detecte() -> None:
    """.git/ mentionné avec .write_text() est détecté."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"from pathlib import Path; Path('.git/config').write_text('x')\""
    )
    assert ".git/" in resultat


def test_node_c_sans_ecriture_non_detecte() -> None:
    """node -c sans mode écriture n'est pas détecté."""
    assert cibles_interpreteur_ecriture("node -c 'console.log(\"hello\")'") == []


def test_node_e_write_to_a_protected_file_is_refused() -> None:
    resultat = cibles_interpreteur_ecriture(
        "node -e \"require('fs').writeFileSync('agents.json','x')\""
    )
    assert resultat == ["agents.json"]


def test_node_append_and_stream_writers_are_refused() -> None:
    assert cibles_interpreteur_ecriture(
        "node -e \"require('fs').appendFileSync('CLAUDE.md','x')\""
    ) == ["CLAUDE.md"]
    assert cibles_interpreteur_ecriture(
        "node --eval \"fs.createWriteStream('.git/config')\""
    ) == [".git/"]


def test_node_e_without_write_passes() -> None:
    assert cibles_interpreteur_ecriture('node -e "console.log(1)"') == []
    assert cibles_interpreteur_ecriture(
        "node -e \"console.log(require('fs').readFileSync('agents.json','utf8'))\""
    ) == []


def test_python_open_with_named_mode_is_refused() -> None:
    assert cibles_interpreteur_ecriture("python -c \"open('agents.json', mode='w')\"") == [
        "agents.json"
    ]


def test_python_open_with_named_read_mode_passes() -> None:
    assert cibles_interpreteur_ecriture("python -c \"open('agents.json', mode='r')\"") == []


def test_python_shutil_copy_to_a_protected_file_is_refused() -> None:
    assert cibles_interpreteur_ecriture("python -c \"shutil.copy('a','agents.json')\"") == [
        "agents.json"
    ]
    assert cibles_interpreteur_ecriture(
        "python3 -c \"import os; os.replace('a','CLAUDE.md')\""
    ) == ["CLAUDE.md"]


async def test_the_hook_refuses_node_e_write(tmp_path: Path) -> None:
    hook = hook_refus_hors_perimetre(_projet(tmp_path))

    sortie = await hook(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "node -e \"require('fs').writeFileSync('agents.json','x')\""
            },
        },
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_the_hook_lets_node_e_console_log_pass(tmp_path: Path) -> None:
    hook = hook_refus_hors_perimetre(_projet(tmp_path))

    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": 'node -e "console.log(1)"'}},
        None,
        None,
    )

    assert sortie == {}


def test_premier_jeton_pas_interprete_non_detecte() -> None:
    """uv n'est pas un interpréteur : pas de détection même avec python -c après."""
    resultat = cibles_interpreteur_ecriture(
        "uv run python -c \"open('CLAUDE.md','w').write('x')\""
    )
    assert resultat == []


def test_python_c_claude_local_md_detecte() -> None:
    """CLAUDE.local.md est aussi un fichier protégé."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"open('CLAUDE.local.md','w').write('x')\""
    )
    assert "CLAUDE.local.md" in resultat


def test_python_c_mode_lecture_explicite_non_detecte() -> None:
    """open('CLAUDE.md', 'r') ne déclenche pas le filtre."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"data = open('CLAUDE.md', 'r').read()\""
    )
    assert resultat == []


def test_python_c_mode_ajout_detecte() -> None:
    """open(..., 'a') est aussi un mode d'écriture."""
    resultat = cibles_interpreteur_ecriture(
        "python -c \"open('CLAUDE.md','a').write('x')\""
    )
    assert "CLAUDE.md" in resultat


# ------------------------------------------------------------------
# Le hook — intégration
# ------------------------------------------------------------------


async def test_le_hook_refuse_python_c_write_claude_md(tmp_path: Path) -> None:
    """Le critère d'acceptation principal : python -c avec CLAUDE.md en écriture."""
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python -c \"open('CLAUDE.md','w').write('x')\""},
        },
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert INTERPRETE_PROTEGE_REFUS[:30] in sortie["hookSpecificOutput"]["permissionDecisionReason"]


async def test_le_hook_laisse_passer_python_c_lecture_seule(tmp_path: Path) -> None:
    """Un python -c qui lit un fichier protégé passe."""
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python -c \"print(open('CLAUDE.md').read())\""},
        },
        None,
        None,
    )

    assert sortie == {}


async def test_le_hook_laisse_passer_python_m_pytest(tmp_path: Path) -> None:
    """python -m pytest reste permis (pas de -c, pas de fichier protégé écrit)."""
    projet = _projet(tmp_path)
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": "python -m pytest"}},
        None,
        None,
    )

    assert sortie == {}
