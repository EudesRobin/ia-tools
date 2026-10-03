#!/usr/bin/env python3
"""Tests de scripts/validate.py : chaque controle est vu en rouge sur un cas
volontairement casse, et le depot reel reste au vert (AGENTS.md, DoD des
scripts). Chaque cas opere sur une copie du depot dans un dossier temporaire.

Usage : python scripts/test_validate.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def copy_repo(dest: Path) -> None:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    for rel in out.stdout.splitlines():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


def append_to(rel: str, text: str):
    def f(d: Path) -> None:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(text)
    return f


def replace_once(rel: str, before: str, after: str):
    def f(d: Path) -> None:
        p = d / rel
        t = p.read_text(encoding="utf-8")
        assert before in t, f"motif absent de {rel} : {before!r}"
        p.write_text(t.replace(before, after, 1), encoding="utf-8")
    return f


# (nom, alteration, fragment attendu dans la sortie)
CASES = [
    ("ancre interne morte", append_to("docs/SETUP.md", "\n[x](#nulle-part)\n"), "ancre interne introuvable"),
    ("ancre externe morte", append_to("README.md", "\n[x](docs/SETUP.md#nulle-part)\n"), "ancre introuvable"),
    ("lien relatif mort", append_to("README.md", "\n[x](./absent.md)\n"), "lien relatif mort"),
    ("lien de reference mort", append_to("README.md", "\n[r]: ./absent.md\n"), "lien relatif mort"),
    ("chemin Windows", append_to("README.md", "\nC:\\Users\\quelquun\\x\n"), "chemin local en dur"),
    ("chemin a barres obliques", append_to("README.md", "\nC:/Users/quelquun/x\n"), "chemin local en dur"),
    ("chemin macOS", append_to("README.md", "\n/Users/quelquun/x\n"), "chemin local en dur"),
    ("placeholder non declare", append_to("skills/setup-harness/SKILL.md", "\n{INCONNU}\n"), "placeholder non declare"),
    ("name different du dossier", replace_once("skills/setup-harness/SKILL.md", "name: setup-harness", "name: autre"), "name='autre'"),
    ("cle de front-matter inconnue", replace_once("agents/audit-docs.md", "tools:", "modele: x\ntools:"), "cle de front-matter non prevue"),
    ("tools d'agent absent", replace_once("agents/audit-docs.md", "tools: Read, Grep, Glob, TodoWrite\n", ""), "champ 'tools'"),
    ("outil hors inventaire", append_to("skills/neuve/SKILL.md", "---\nname: neuve\ndescription: Test.\n---\n"), "absent de l'inventaire"),
    ("syntaxe Python", append_to("scripts/install.py", "\ndef (:\n"), "erreur de syntaxe"),
    ("JSON d'enregistrement", replace_once(".claude/settings.json", "{", "{ ,"), "JSON invalide"),
    ("script de hook introuvable", replace_once(".github/hooks/validate-tool.json", "validate-tool.ps1", "absent.ps1"), "script de hook introuvable"),
    ("status line hors inventaire", append_to("statuslines/claude/neuve/STATUSLINE.md", "# Status line\n"), "statuslines/claude/neuve : absent de l'inventaire"),
    ("script de status line manquant", lambda d: (d / "statuslines/claude/usage-session/statusline.ps1").unlink(), "statusline.ps1 manquant"),
    ("status line hors dossier d'agent hote", append_to("statuslines/neuve/STATUSLINE.md", "# Status line\n"), "statuslines/neuve : pas un dossier d'agent hote"),
    ("document hors table", append_to("docs/NOUVEAU.md", "# Nouveau\n"), "non enregistre"),
    ("journal mal forme", replace_once("CHANGELOG.md", "### 🚀 Nouveautés", "### Divers"), "rubrique non prevue 'Divers'"),
    ("journal manquant", lambda d: (d / "CHANGELOG.md").unlink(), "CHANGELOG.md manquant"),
    ("fichier non UTF-8", lambda d: (d / "README.md").write_text("# Titre\n", encoding="utf-16"), "illisible en UTF-8"),
]

# Controle saute par validate.py quand pwsh est absent : teste seulement s'il est present.
if shutil.which("pwsh"):
    CASES.append((
        "syntaxe PowerShell",
        append_to("hooks/validate-tool/validate-tool.ps1", "\nif ($x {\n"),
        "erreur de syntaxe PowerShell",
    ))
    CASES.append((
        "syntaxe PowerShell d'une status line",
        append_to("statuslines/claude/usage-session/statusline.ps1", "\nif ($x {\n"),
        "statuslines/claude/usage-session/statusline.ps1:",
    ))


class TestValidate(unittest.TestCase):
    def run_validate(self, alteration=None, ci: bool = False) -> subprocess.CompletedProcess:
        # GITHUB_ACTIONS est fixe par le test, pas herite : meme resultat en local et en CI.
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
        if ci:
            env["GITHUB_ACTIONS"] = "true"
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            copy_repo(d)
            if alteration:
                alteration(d)
            return subprocess.run(
                [sys.executable, str(d / "scripts" / "validate.py")],
                cwd=d, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
            )

    def test_real_repo_passes(self):
        r = self.run_validate()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_broken_cases_fail(self):
        for name, alteration, expected in CASES:
            with self.subTest(name):
                r = self.run_validate(alteration)
                self.assertEqual(r.returncode, 1, f"{name} : reste vert")
                self.assertIn(expected, r.stdout, f"{name} : message attendu absent")

    def test_annotations(self):
        """En CI, chaque ecart est emis en annotation rattachee a son fichier et a sa ligne."""
        dead_link = append_to("README.md", "\n[x](./absent.md)\n")
        r = self.run_validate(dead_link)
        self.assertNotIn("::error", r.stdout, "annotation emise hors CI")
        r = self.run_validate(dead_link, ci=True)
        expected_line = len((ROOT / "README.md").read_text(encoding="utf-8").splitlines()) + 2
        self.assertIn(
            f"::error file=README.md,line={expected_line},title=validate.py::README.md:{expected_line} : lien relatif mort",
            r.stdout,
        )
        r = self.run_validate(append_to("scripts/install.py", "\ndef (:\n"), ci=True)
        self.assertRegex(r.stdout, r"::error file=scripts/install\.py,line=\d+,title=validate\.py::")


if __name__ == "__main__":
    unittest.main(verbosity=2)
