#!/usr/bin/env python3
"""Tests de skills/release/journal_version.py, sans depot reel : un faux git
renvoie des sorties enregistrees. Chaque refus de --close est vu en rouge sur
un cas volontairement casse (AGENTS.md, DoD des scripts).

Usage : python tests/test_journal_version.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "release" / "journal_version.py"

FAKE_GIT = '''
import json, os, sys
key = " ".join(sys.argv[1:])
fixtures = json.load(open(os.environ["FAKE_FIXTURES"], encoding="utf-8"))
entry = fixtures.get(key, {"code": 1, "err": "commande non prevue : " + key})
sys.stdout.write(entry.get("out", ""))
sys.exit(entry.get("code", 0))
'''

FR = """# Journal des modifications

## [Non publié]

### 🚀 Nouveautés

- Outil A.

### 🐛 Corrections

- Correction B.

## [1.4.1] - 2026-10-10

### 🐛 Corrections

- Correction C.

[Non publié]: https://github.com/org/depot/compare/1.4.1...HEAD
[1.4.1]: https://github.com/org/depot/compare/1.4.0...1.4.1
"""

EN = """# Changelog

## [Unreleased]

### Fixed

- Bug.

## [0.3.0] - 2026-01-02

### Added

- Feature.

[Unreleased]: https://github.com/org/depot/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/org/depot/compare/v0.2.0...v0.3.0
"""


class JournalVersionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.repo = self.dir / "depot"
        self.repo.mkdir()
        self.git = self.dir / "fake_git.py"
        self.git.write_text(FAKE_GIT, encoding="utf-8")
        self.set_repo(FR, tags="1.4.1\n1.4.0\n")

    def tearDown(self):
        self.tmp.cleanup()

    def set_repo(self, changelog, tags="", newline="\n"):
        (self.repo / "CHANGELOG.md").write_bytes(changelog.replace("\n", newline).encode("utf-8"))
        fixtures = {
            "rev-parse --show-toplevel": {"out": self.repo.as_posix() + "\n"},
            "rev-parse --absolute-git-dir": {"out": (self.repo / ".git").as_posix() + "\n"},
            "tag --list --sort=-v:refname": {"out": tags},
        }
        path = self.dir / "fixtures.json"
        path.write_text(json.dumps(fixtures), encoding="utf-8")
        self.env = {**os.environ, "FAKE_FIXTURES": str(path), "PYTHONUTF8": "1"}

    def run_script(self, *args):
        res = subprocess.run([sys.executable, str(SCRIPT), "--git", str(self.git), *args],
                             capture_output=True, env=self.env, cwd=self.repo)
        return res.returncode, (res.stdout + res.stderr).decode("utf-8").replace("\r\n", "\n")

    def field(self, out, key):
        for line in out.splitlines():
            name, _, value = line.partition(" : ")
            if name.strip() == key:
                return value
        self.fail(f"champ {key} absent :\n{out}")

    def changelog(self):
        return (self.repo / "CHANGELOG.md").read_bytes().decode("utf-8")

    # ---------------------------------------------------------------- etat

    def test_state_french_emoji_headings(self):
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "section_non_publiee"), "Non publié")
        self.assertEqual(self.field(out, "entrees"), "2")
        self.assertEqual(self.field(out, "derniere_version"), "1.4.1 (2026-10-10)")
        self.assertEqual(self.field(out, "tag_pose"), "oui (1.4.1)")
        self.assertEqual(self.field(out, "proposition"), "1.5.0 (mineur depuis 1.4.1)")
        self.assertEqual(self.field(out, "liens"), "comparaison")
        self.assertEqual(self.field(out, "workflow_release"), "aucun")
        self.assertEqual(self.field(out, "git_dir"), (self.repo / ".git").as_posix())
        self.assertLess(len(out.splitlines()), 20, "sortie trop longue")

    def test_state_patch_only(self):
        self.set_repo(EN, tags="v0.3.0\nv0.2.0\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "prefixe_tag"), "v")
        self.assertEqual(self.field(out, "tag_pose"), "oui (v0.3.0)")
        self.assertEqual(self.field(out, "proposition"), "0.3.1 (correctif depuis 0.3.0)")

    def test_state_major_and_zero_major(self):
        self.set_repo(FR.replace("### 🐛 Corrections\n\n- Correction B.",
                                 "### 🔥 Suppressions\n\n- Outil D retire."), tags="1.4.1\n")
        code, out = self.run_script()
        self.assertEqual(self.field(out, "proposition"), "2.0.0 (majeur depuis 1.4.1)")
        self.set_repo(EN.replace("### Fixed", "### Removed"), tags="v0.3.0\n")
        code, out = self.run_script()
        self.assertTrue(self.field(out, "proposition").startswith("0.4.0 (majeur depuis 0.3.0 ; version 0.y.z"), out)

    def test_state_closed_but_not_tagged(self):
        self.set_repo(FR.replace("### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n", ""),
                      tags="1.4.0\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "entrees"), "0")
        self.assertEqual(self.field(out, "tag_pose"), "non (1.4.1)")
        self.assertTrue(self.field(out, "proposition").startswith("aucune"))

    def test_state_unknown_heading_and_release_workflow(self):
        wf = self.repo / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "release.yml").write_text("on:\n  push:\n    tags: ['*']\n", encoding="utf-8")
        (wf / "ci.yml").write_text("on:\n  push:\n    branches: [main]\n", encoding="utf-8")
        self.set_repo(FR.replace("### 🐛 Corrections", "### Divers"), tags="1.4.1\n")
        code, out = self.run_script()
        self.assertEqual(self.field(out, "rubriques_inconnues"), "Divers")
        self.assertEqual(self.field(out, "workflow_release"), "release.yml")

    def test_missing_changelog_is_environment_error(self):
        (self.repo / "CHANGELOG.md").unlink()
        code, out = self.run_script()
        self.assertEqual(code, 2, out)

    def test_git_missing_is_environment_error(self):
        res = subprocess.run([sys.executable, str(SCRIPT), "--git", str(self.dir / "absent.py")],
                             capture_output=True, env=self.env, cwd=self.repo)
        self.assertEqual(res.returncode, 2)

    # ------------------------------------------------------------- cloture

    def test_close_rewrites_sections_and_links(self):
        code, out = self.run_script("--close", "1.5.0", "--date", "2026-10-12")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "liens"), "mis a jour")
        text = self.changelog()
        self.assertIn("## [Non publié]\n\n## [1.5.0] - 2026-10-12\n\n### 🚀 Nouveautés", text)
        self.assertIn("[Non publié]: https://github.com/org/depot/compare/1.5.0...HEAD\n"
                      "[1.5.0]: https://github.com/org/depot/compare/1.4.1...1.5.0\n"
                      "[1.4.1]:", text)
        code, out = self.run_script()
        self.assertEqual(self.field(out, "entrees"), "0")
        self.assertEqual(self.field(out, "tag_pose"), "non (1.5.0)")

    def test_close_keeps_crlf_and_tag_prefix(self):
        self.set_repo(EN, tags="v0.3.0\n", newline="\r\n")
        code, out = self.run_script("--close", "0.3.1", "--date", "2026-10-12")
        self.assertEqual(code, 0, out)
        text = self.changelog()
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertIn("[0.3.1]: https://github.com/org/depot/compare/v0.3.0...v0.3.1", text)

    def test_close_refuses_empty_section(self):
        self.set_repo(FR.replace("- Outil A.", "").replace("- Correction B.", ""), tags="1.4.1\n")
        before = self.changelog()
        code, out = self.run_script("--close", "1.5.0")
        self.assertEqual(code, 1, out)
        self.assertIn("sans entree", out)
        self.assertEqual(self.changelog(), before)

    def test_close_refuses_version_not_greater(self):
        code, out = self.run_script("--close", "1.4.1")
        self.assertEqual(code, 1, out)
        self.assertIn("pas superieure", out)

    def test_close_refuses_existing_tag(self):
        self.set_repo(FR, tags="1.6.0\n1.4.1\n")
        code, out = self.run_script("--close", "1.6.0")
        self.assertEqual(code, 1, out)
        self.assertIn("1.6.0", out)

    def test_close_refuses_bad_version_and_date(self):
        self.assertEqual(self.run_script("--close", "v1.5.0")[0], 1)
        self.assertEqual(self.run_script("--close", "1.5")[0], 1)
        self.assertEqual(self.run_script("--close", "1.5.0", "--date", "12/10/2026")[0], 1)

    # --------------------------------------------------------------- notes

    def test_notes(self):
        code, out = self.run_script("--notes", "1.4.1")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.strip(), "### 🐛 Corrections\n\n- Correction C.")
        self.assertEqual(self.run_script("--notes", "9.9.9")[0], 1)

    def test_close_and_notes_are_exclusive(self):
        self.assertEqual(self.run_script("--close", "1.5.0", "--notes", "1.4.1")[0], 1)


if __name__ == "__main__":
    unittest.main()
