#!/usr/bin/env python3
"""Tests de scripts/validate.py : chaque controle est vu en rouge sur un cas
volontairement casse, et le depot reel reste au vert (AGENTS.md, DoD des
scripts). Chaque cas opere sur une copie du depot dans un dossier temporaire.

Usage : python scripts/test_validate.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def copie_depot(dest: Path) -> None:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    for rel in out.stdout.splitlines():
        cible = dest / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, cible)


def ajouter(rel: str, texte: str):
    def f(d: Path) -> None:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(texte)
    return f


def remplacer(rel: str, avant: str, apres: str):
    def f(d: Path) -> None:
        p = d / rel
        t = p.read_text(encoding="utf-8")
        assert avant in t, f"motif absent de {rel} : {avant!r}"
        p.write_text(t.replace(avant, apres, 1), encoding="utf-8")
    return f


# (nom, alteration, fragment attendu dans la sortie)
CAS = [
    ("ancre interne morte", ajouter("docs/SETUP.md", "\n[x](#nulle-part)\n"), "ancre interne introuvable"),
    ("ancre externe morte", ajouter("README.md", "\n[x](docs/SETUP.md#nulle-part)\n"), "ancre introuvable"),
    ("lien relatif mort", ajouter("README.md", "\n[x](./absent.md)\n"), "lien relatif mort"),
    ("lien de reference mort", ajouter("README.md", "\n[r]: ./absent.md\n"), "lien relatif mort"),
    ("chemin Windows", ajouter("README.md", "\nC:\\Users\\quelquun\\x\n"), "chemin local en dur"),
    ("chemin a barres obliques", ajouter("README.md", "\nC:/Users/quelquun/x\n"), "chemin local en dur"),
    ("chemin macOS", ajouter("README.md", "\n/Users/quelquun/x\n"), "chemin local en dur"),
    ("placeholder non declare", ajouter("skills/setup-harness/SKILL.md", "\n{INCONNU}\n"), "placeholder non declare"),
    ("name different du dossier", remplacer("skills/setup-harness/SKILL.md", "name: setup-harness", "name: autre"), "name='autre'"),
    ("cle de front-matter inconnue", remplacer("agents/audit-docs.md", "tools:", "modele: x\ntools:"), "cle de front-matter non prevue"),
    ("tools d'agent absent", remplacer("agents/audit-docs.md", "tools: Read, Grep, Glob, TodoWrite\n", ""), "champ 'tools'"),
    ("outil hors inventaire", ajouter("skills/neuve/SKILL.md", "---\nname: neuve\ndescription: Test.\n---\n"), "absent de l'inventaire"),
    ("syntaxe Python", ajouter("scripts/install.py", "\ndef (:\n"), "erreur de syntaxe"),
    ("JSON d'enregistrement", remplacer(".claude/settings.json", "{", "{ ,"), "JSON invalide"),
    ("script de hook introuvable", remplacer(".github/hooks/validate-tool.json", "validate-tool.ps1", "absent.ps1"), "script de hook introuvable"),
    ("status line hors inventaire", ajouter("statuslines/claude/neuve/STATUSLINE.md", "# Status line\n"), "statuslines/claude/neuve : absent de l'inventaire"),
    ("script de status line manquant", lambda d: (d / "statuslines/claude/usage-session/statusline.ps1").unlink(), "statusline.ps1 manquant"),
    ("status line hors dossier d'agent hote", ajouter("statuslines/neuve/STATUSLINE.md", "# Status line\n"), "statuslines/neuve : pas un dossier d'agent hote"),
    ("document hors table", ajouter("docs/NOUVEAU.md", "# Nouveau\n"), "non enregistre"),
    ("fichier non UTF-8", lambda d: (d / "README.md").write_text("# Titre\n", encoding="utf-16"), "illisible en UTF-8"),
]

# Controle saute par validate.py quand pwsh est absent : teste seulement s'il est present.
if shutil.which("pwsh"):
    CAS.append((
        "syntaxe PowerShell",
        ajouter("hooks/validate-tool/validate-tool.ps1", "\nif ($x {\n"),
        "erreur de syntaxe PowerShell",
    ))
    CAS.append((
        "syntaxe PowerShell d'une status line",
        ajouter("statuslines/claude/usage-session/statusline.ps1", "\nif ($x {\n"),
        "statuslines/claude/usage-session/statusline.ps1:",
    ))


class TestValidate(unittest.TestCase):
    def lancer(self, alteration=None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            copie_depot(d)
            if alteration:
                alteration(d)
            return subprocess.run(
                [sys.executable, str(d / "scripts" / "validate.py")],
                cwd=d, capture_output=True, text=True, stdin=subprocess.DEVNULL,
            )

    def test_depot_reel_vert(self):
        r = self.lancer()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_cas_casses_rouges(self):
        for nom, alteration, attendu in CAS:
            with self.subTest(nom):
                r = self.lancer(alteration)
                self.assertEqual(r.returncode, 1, f"{nom} : reste vert")
                self.assertIn(attendu, r.stdout, f"{nom} : message attendu absent")


if __name__ == "__main__":
    unittest.main(verbosity=2)
