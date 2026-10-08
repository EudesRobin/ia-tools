#!/usr/bin/env python3
"""Tests de scripts/changelog.py : journal conforme admis, chaque ecart de
structure vu en rouge, extraction d'une section, et refus d'une plage qui
modifie un outil sans entree du journal (depot git temporaire).

Usage : python tests/test_changelog.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "changelog.py"
sys.path.insert(0, str(SCRIPT.parent))
from changelog import structure_issues, version_notes  # noqa: E402

VALID = """# Journal des modifications

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


def replace_once(before: str, after: str) -> str:
    assert before in VALID, before
    return VALID.replace(before, after, 1)


# (nom, journal altere, fragment attendu dans un ecart)
BROKEN = [
    ("sans Non publie en tete", replace_once("## [Non publié]\n\n### 🧹 Maintenance\n\n- Entree non publiee.\n\n", ""),
     "premiere section"),
    ("Non publie date", replace_once("## [Non publié]", "## [Non publié] - 2026-10-02"), "premiere section"),
    ("version mal formee", replace_once("## [1.0.0] - 2026-09-27", "## [v1.0.0] - 2026-09-27"), "non conforme"),
    ("date invalide", replace_once("## [1.0.0] - 2026-09-27", "## [1.0.0] - 2026-13-40"), "date absente ou invalide"),
    ("date absente", replace_once("## [1.0.0] - 2026-09-27", "## [1.0.0]"), "date absente ou invalide"),
    ("versions non decroissantes", replace_once("## [1.0.0] - 2026-09-27", "## [1.2.0] - 2026-09-27"),
     "non decroissante"),
    ("rubrique inconnue", replace_once("### 📝 Documentation", "### Divers"), "rubrique non prevue"),
    ("rubrique sans emoji", replace_once("### 📝 Documentation", "### Documentation"), "rubrique non prevue"),
    ("rubriques dans le desordre", replace_once("### 🚀 Nouveautés\n\n- Outil ajoute.\n\n### 📝 Documentation\n\n- Precision.",
                                            "### 📝 Documentation\n\n- Precision.\n\n### 🚀 Nouveautés\n\n- Outil ajoute."),
     "hors de l'ordre prevu"),
    ("rubrique vide", replace_once("### 📝 Documentation\n\n- Precision.\n", "### 📝 Documentation\n"), "sans entree"),
    ("entree hors rubrique", replace_once("## [1.0.0] - 2026-09-27\n", "## [1.0.0] - 2026-09-27\n\n- Orpheline.\n"),
     "entree hors rubrique"),
]


class TestStructure(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(structure_issues(VALID), [])

    def test_broken(self):
        for name, text, expected in BROKEN:
            with self.subTest(name):
                found = structure_issues(text)
                self.assertTrue(any(expected in e for e in found), f"{name} : {found}")

    def test_issue_has_line(self):
        text = replace_once("### 📝 Documentation", "### Divers")
        line = text.splitlines().index("### Divers") + 1
        found = structure_issues(text)
        self.assertIn(f"CHANGELOG.md:{line} : rubrique non prevue 'Divers'", found)


class TestVersionNotes(unittest.TestCase):
    def test_notes_extracted(self):
        body = version_notes(VALID, "1.1.0")
        self.assertTrue(body.startswith("### 🚀 Nouveautés"), body)
        self.assertIn("- Precision.", body)
        self.assertNotIn("1.0.0", body)
        self.assertNotIn("https://", body)

    def test_notes_missing(self):
        self.assertIsNone(version_notes(VALID, "9.9.9"))


class TestRequireEntry(unittest.TestCase):
    """--require-entry, sur un depot temporaire contenant une copie du script."""

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

    def commit(self, files: dict, message: str) -> str:
        for rel, content in files.items():
            p = self.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run_check(self, head: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.d / "scripts" / "changelog.py"), "--require-entry", f"{self.base}..{head}"],
            cwd=self.d, env=os.environ.copy(), capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )

    def test_tool_without_entry(self):
        head = self.commit({"skills/x/SKILL.md": "x\n"}, "feat: x")
        r = self.run_check(head)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("skills/x/SKILL.md", r.stderr)

    def test_install_without_entry(self):
        head = self.commit({"scripts/install.py": "x\n"}, "fix: x")
        self.assertEqual(self.run_check(head).returncode, 1)

    def test_tool_with_entry(self):
        head = self.commit({"skills/x/SKILL.md": "x\n", "CHANGELOG.md": "x\n"}, "feat: x")
        r = self.run_check(head)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_outside_tools(self):
        head = self.commit({"docs/x.md": "x\n"}, "docs: x")
        r = self.run_check(head)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
