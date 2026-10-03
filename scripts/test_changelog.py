#!/usr/bin/env python3
"""Tests de scripts/changelog.py : journal conforme admis, chaque ecart de
structure vu en rouge, extraction d'une section, et refus d'une plage qui
modifie un outil sans entree du journal (depot git temporaire).

Usage : python scripts/test_changelog.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "changelog.py"
sys.path.insert(0, str(SCRIPT.parent))
from changelog import ecarts_structure, section  # noqa: E402

CONFORME = """# Journal des modifications

## [Non publié]

### 🧹 Maintenance

- Entree non publiee.

## [1.1.0] - 2026-10-01

### 🚀 Nouveautés

- Outil ajoute.

### 📝 Documentation

- Precision.

## [1.0.0] - 2026-09-27

### 🚀 Nouveautés

- Premiere version.

[Non publié]: https://example.org/compare/1.1.0...HEAD
[1.1.0]: https://example.org/compare/1.0.0...1.1.0
"""


def remplacer(avant: str, apres: str) -> str:
    assert avant in CONFORME, avant
    return CONFORME.replace(avant, apres, 1)


# (nom, journal altere, fragment attendu dans un ecart)
ECARTS = [
    ("sans Non publie en tete", remplacer("## [Non publié]\n\n### 🧹 Maintenance\n\n- Entree non publiee.\n\n", ""),
     "premiere section"),
    ("Non publie date", remplacer("## [Non publié]", "## [Non publié] - 2026-10-02"), "premiere section"),
    ("version mal formee", remplacer("## [1.0.0] - 2026-09-27", "## [v1.0.0] - 2026-09-27"), "non conforme"),
    ("date invalide", remplacer("## [1.0.0] - 2026-09-27", "## [1.0.0] - 2026-13-40"), "date absente ou invalide"),
    ("date absente", remplacer("## [1.0.0] - 2026-09-27", "## [1.0.0]"), "date absente ou invalide"),
    ("versions non decroissantes", remplacer("## [1.0.0] - 2026-09-27", "## [1.2.0] - 2026-09-27"),
     "non decroissante"),
    ("rubrique inconnue", remplacer("### 📝 Documentation", "### Divers"), "rubrique non prevue"),
    ("rubrique sans emoji", remplacer("### 📝 Documentation", "### Documentation"), "rubrique non prevue"),
    ("rubriques dans le desordre", remplacer("### 🚀 Nouveautés\n\n- Outil ajoute.\n\n### 📝 Documentation\n\n- Precision.",
                                            "### 📝 Documentation\n\n- Precision.\n\n### 🚀 Nouveautés\n\n- Outil ajoute."),
     "hors de l'ordre prevu"),
    ("rubrique vide", remplacer("### 📝 Documentation\n\n- Precision.\n", "### 📝 Documentation\n"), "sans entree"),
    ("entree hors rubrique", remplacer("## [1.0.0] - 2026-09-27\n", "## [1.0.0] - 2026-09-27\n\n- Orpheline.\n"),
     "entree hors rubrique"),
]


class TestStructure(unittest.TestCase):
    def test_conforme(self):
        self.assertEqual(ecarts_structure(CONFORME), [])

    def test_ecarts(self):
        for nom, texte, attendu in ECARTS:
            with self.subTest(nom):
                trouves = ecarts_structure(texte)
                self.assertTrue(any(attendu in e for e in trouves), f"{nom} : {trouves}")

    def test_ecart_situe(self):
        texte = remplacer("### 📝 Documentation", "### Divers")
        ligne = texte.splitlines().index("### Divers") + 1
        trouves = ecarts_structure(texte)
        self.assertIn(f"CHANGELOG.md:{ligne} : rubrique non prevue 'Divers'", trouves)


class TestSection(unittest.TestCase):
    def test_section_extraite(self):
        corps = section(CONFORME, "1.1.0")
        self.assertTrue(corps.startswith("### 🚀 Nouveautés"), corps)
        self.assertIn("- Precision.", corps)
        self.assertNotIn("1.0.0", corps)
        self.assertNotIn("https://", corps)

    def test_section_absente(self):
        self.assertIsNone(section(CONFORME, "9.9.9"))


class TestExigeEntree(unittest.TestCase):
    """--exige-entree, sur un depot temporaire contenant une copie du script."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        (self.d / "scripts").mkdir()
        (self.d / "scripts" / "changelog.py").write_bytes(SCRIPT.read_bytes())
        self.git("init", "-q")
        self.base = self.commit({"README.md": "x\n"}, "chore: base")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=", *args],
            cwd=self.d, capture_output=True, text=True, check=True,
        ).stdout.strip()

    def commit(self, fichiers: dict, message: str) -> str:
        for rel, contenu in fichiers.items():
            p = self.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenu, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def lancer(self, head: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.d / "scripts" / "changelog.py"), "--exige-entree", f"{self.base}..{head}"],
            cwd=self.d, env=os.environ.copy(), capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )

    def test_outil_sans_entree(self):
        head = self.commit({"skills/x/SKILL.md": "x\n"}, "feat: x")
        r = self.lancer(head)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("skills/x/SKILL.md", r.stderr)

    def test_install_sans_entree(self):
        head = self.commit({"scripts/install.py": "x\n"}, "fix: x")
        self.assertEqual(self.lancer(head).returncode, 1)

    def test_outil_avec_entree(self):
        head = self.commit({"skills/x/SKILL.md": "x\n", "CHANGELOG.md": "x\n"}, "feat: x")
        r = self.lancer(head)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_hors_outil(self):
        head = self.commit({"docs/x.md": "x\n"}, "docs: x")
        r = self.lancer(head)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
