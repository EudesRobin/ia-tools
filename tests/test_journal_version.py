#!/usr/bin/env python3
"""Tests de skills/release/journal_version.py, sans depot reel ni GitHub : un
faux git et un faux gh renvoient des sorties enregistrees. Chaque refus et
chaque verification sont vus en rouge sur un cas volontairement casse
(AGENTS.md, DoD des scripts).

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

FAKE = '''
import json, os, sys
key = " ".join([TOOL, *sys.argv[1:]])
fixtures = json.load(open(os.environ["FAKE_FIXTURES"], encoding="utf-8"))
entry = fixtures.get(key, {"code": 1, "err": "commande non prevue : " + key})
sys.stdout.buffer.write(entry.get("out", "").encode("utf-8"))
sys.stderr.write(entry.get("err", ""))
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

[unreleased]: https://github.com/org/depot/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/org/depot/compare/v0.2.0...v0.3.0
"""

CLOSED = FR.replace("## [Non publié]\n\n", "## [Non publié]\n\n## [1.5.0] - 2026-10-12\n\n")

RELEASE_WF = "name: release\non:\n  push:\n    tags: ['*']\njobs:\n  r:\n    steps:\n      - run: gh release create x\n"
DOCKER_WF = ("name: docker\non:\n  push:\n    branches: [main]\njobs:\n  d:\n    steps:\n"
             "      - uses: docker/metadata-action@v5\n        with:\n          tags: |\n            latest\n")
PYPI_WF = "name: pypi\non:\n  push:\n    tags:\n      - 'v*'\njobs:\n  p:\n    steps:\n      - run: twine upload\n"


def ok(out=""):
    return {"code": 0, "out": out}


def fail(err="", code=1):
    return {"code": code, "err": err}


class JournalVersionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.repo = self.dir / "depot"
        self.repo.mkdir()
        for tool in ("git", "gh"):
            (self.dir / f"fake_{tool}.py").write_text(FAKE.replace("TOOL", repr(tool)), encoding="utf-8")
        self.set_repo(FR, tags=["1.4.1", "1.4.0"])

    def tearDown(self):
        self.tmp.cleanup()

    def set_repo(self, changelog, tags=(), remote=None, shared=None, newline="\n", **over):
        """Journal local, tags locaux et distants, journal de origin/main."""
        (self.repo / "CHANGELOG.md").write_bytes(changelog.replace("\n", newline).encode("utf-8"))
        remote = tags if remote is None else remote
        f = {
            "git rev-parse --show-toplevel": ok(self.repo.as_posix() + "\n"),
            "git rev-parse --absolute-git-dir": ok((self.repo / ".git").as_posix() + "\n"),
            "git remote": ok("origin\n"),
            "git symbolic-ref --short refs/remotes/origin/HEAD": ok("origin/main\n"),
            "git tag --list --sort=-v:refname": ok("".join(t + "\n" for t in tags)),
            "git ls-remote --tags origin": ok("".join(f"abc\trefs/tags/{t}\n" for t in remote)),
            "git show origin/main:CHANGELOG.md": ok(changelog if shared is None else shared),
        }
        f.update(over)
        self.fixtures = f
        path = self.dir / "fixtures.json"
        path.write_text(json.dumps(f), encoding="utf-8")
        self.env = {**os.environ, "FAKE_FIXTURES": str(path), "PYTHONUTF8": "1",
                    "JOURNAL_VERSION_FAKE_GIT": str(self.dir / "fake_git.py"),
                    "JOURNAL_VERSION_FAKE_GH": str(self.dir / "fake_gh.py")}

    def run_script(self, *args):
        res = subprocess.run([sys.executable, str(SCRIPT), *args],
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

    def workflow(self, name, text):
        folder = self.repo / ".github" / "workflows"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")

    # ---------------------------------------------------------------- etat

    def test_state_french_emoji_headings(self):
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "section_non_publiee"), "Non publié")
        self.assertEqual(self.field(out, "entrees"), "2")
        self.assertEqual(self.field(out, "base"), "main")
        self.assertEqual(self.field(out, "git_dir"), (self.repo / ".git").as_posix())
        self.assertEqual(self.field(out, "proposition"), "1.5.0 (mineur depuis 1.4.1)")
        self.assertEqual(self.field(out, "liens"), "comparaison")
        self.assertEqual(self.field(out, "workflow_release"), "aucun")
        self.assertEqual(self.field(out, "fichiers_version"), "aucun")
        self.assertEqual(self.field(out, "etape"), "nouvelle")
        self.assertLess(len(out.splitlines()), 20, "sortie trop longue")

    def test_state_patch_only_and_tag_prefix(self):
        self.set_repo(EN, tags=["v0.3.0", "v0.2.0"])
        code, out = self.run_script()
        self.assertEqual(self.field(out, "prefixe_tag"), "v")
        self.assertEqual(self.field(out, "proposition"), "0.3.1 (correctif depuis 0.3.0)")
        self.assertEqual(self.field(out, "liens"), "comparaison")  # [unreleased] en minuscules

    def test_state_major_and_zero_major(self):
        self.set_repo(FR.replace("### 🐛 Corrections\n\n- Correction B.", "### 🔥 Suppressions\n\n- D retire."),
                      tags=["1.4.1"])
        self.assertEqual(self.field(self.run_script()[1], "proposition"), "2.0.0 (majeur depuis 1.4.1)")
        self.set_repo(EN.replace("### Fixed", "### Removed"), tags=["v0.3.0"])
        self.assertTrue(self.field(self.run_script()[1], "proposition").startswith("0.4.0 (majeur depuis 0.3.0 ; version 0.y.z"))

    def test_state_unknown_heading_and_loose_entries(self):
        self.set_repo(FR.replace("### 🐛 Corrections\n\n- Correction B.", "### Divers\n\n- Autre.")
                        .replace("## [Non publié]\n\n", "## [Non publié]\n\n- Entree libre.\n\n"), tags=["1.4.1"])
        code, out = self.run_script()
        self.assertEqual(self.field(out, "entrees"), "3")
        self.assertEqual(self.field(out, "rubriques_inconnues"), "sans rubrique, Divers (ecartees du calcul)")

    def test_state_workflows(self):
        self.workflow("release.yml", RELEASE_WF)
        self.workflow("docker.yml", DOCKER_WF)
        self.workflow("pypi.yml", PYPI_WF)
        code, out = self.run_script()
        self.assertEqual(self.field(out, "workflow_release"),
                         "pypi.yml (sans creation de Release), release.yml (cree la Release)")

    def test_state_version_files(self):
        (self.repo / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.4.1"\n', encoding="utf-8")
        (self.repo / "package.json").write_text('{"name": "x", "version": "1.4.1"}', encoding="utf-8")
        code, out = self.run_script()
        self.assertEqual(self.field(out, "fichiers_version"), "pyproject.toml (1.4.1), package.json (1.4.1)")

    def test_state_prefix_from_links_without_tags(self):
        self.set_repo(EN, tags=[])
        self.assertEqual(self.field(self.run_script()[1], "prefixe_tag"), "v")
        self.set_repo(EN.split("[unreleased]")[0], tags=[])
        self.assertTrue(self.field(self.run_script()[1], "prefixe_tag").startswith("indetermine"))

    def test_tag_prefix_option(self):
        # Cas casse : prefixe indetermine, choisi par l'utilisateur.
        self.set_repo(EN.split("[unreleased]")[0], tags=[])
        code, out = self.run_script("--tag-prefix", "v")
        self.assertEqual(self.field(out, "prefixe_tag"), "v")
        self.assertEqual(self.field(self.run_script("--tag-prefix", "none")[1], "prefixe_tag"), "aucun")
        self.assertEqual(self.run_script("--tag-prefix", "x")[0], 1)

    def test_state_tolerant_headings(self):
        text = ("# C\n\n## [Unreleased]\n\n### Fixed\n\n- x.\n\n## [1.2.0] — 2024-01-01\n\n### Added\n\n- a.\n\n"
                "## v1.1.0 (2023-01-01)\n\n### Added\n\n- b.\n\n## [0.0.5] - 2014-12-13 [YANKED]\n\n### Added\n\n- c.\n")
        self.set_repo(text, tags=[])
        code, out = self.run_script()
        self.assertEqual(self.field(out, "derniere_version"), "1.2.0 (2024-01-01)")
        self.assertEqual(self.field(out, "proposition"), "1.2.1 (correctif depuis 1.2.0)")
        code, out = self.run_script("--close", "1.1.5")
        self.assertEqual(code, 1, out)

    def test_state_bom_and_non_utf8(self):
        (self.repo / "CHANGELOG.md").write_bytes("\ufeff".encode("utf-8") + FR.encode("utf-8"))
        self.assertEqual(self.field(self.run_script()[1], "section_non_publiee"), "Non publié")
        (self.repo / "CHANGELOG.md").write_bytes(FR.encode("utf-16"))
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("illisible en UTF-8", out)
        self.assertNotIn("Traceback", out)

    def test_file_outside_repository(self):
        outside = self.dir / "AUTRE.md"
        outside.write_text(FR, encoding="utf-8")
        code, out = self.run_script("--file", str(outside))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "journal"), outside.as_posix())

    def test_environment_errors(self):
        (self.repo / "CHANGELOG.md").unlink()
        self.assertEqual(self.run_script()[0], 2)
        self.env["JOURNAL_VERSION_FAKE_GIT"] = str(self.dir / "absent.py")
        self.assertEqual(self.run_script()[0], 2)

    # -------------------------------------------------------------- etapes

    def test_step_tag_when_closed_on_base_and_not_tagged(self):
        self.set_repo(CLOSED, tags=["1.4.1"])
        self.assertEqual(self.field(self.run_script()[1], "etape"), "tag (1.5.0, close sur origin/main)")

    def test_step_waits_for_merge(self):
        # Cas casse : cloture faite sur la branche de travail, PR non mergee.
        self.set_repo(CLOSED, tags=["1.4.1"], shared=FR)
        self.assertEqual(self.field(self.run_script()[1], "etape"),
                         "attente_merge (1.5.0, close localement, absente de origin/main)")

    def test_step_local_tag_not_pushed(self):
        # Cas casse : tag cree localement, push echoue.
        self.set_repo(CLOSED, tags=["1.5.0", "1.4.1"], remote=["1.4.1"])
        self.assertTrue(self.field(self.run_script()[1], "etape").startswith("tag (1.5.0"))

    def test_step_release_missing_then_done(self):
        empty = FR.replace("### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n", "")
        self.set_repo(empty, tags=["1.4.1"], **{
            "gh release view 1.4.1 --json url,isDraft": fail("release not found")})
        self.assertEqual(self.field(self.run_script()[1], "etape"), "release (1.4.1, tag pose, Release absente)")
        self.set_repo(empty, tags=["1.4.1"], **{
            "gh release view 1.4.1 --json url,isDraft": ok('{"url": "https://x/1.4.1", "isDraft": false}')})
        self.assertEqual(self.field(self.run_script()[1], "etape"), "rien")

    def test_step_uses_base_not_stale_local(self):
        # Cas casse : reprise sur main sans pull, journal local encore plein.
        self.set_repo(FR, tags=["1.4.1"], shared=CLOSED)
        self.assertTrue(self.field(self.run_script()[1], "etape").startswith("tag (1.5.0"))

    # ------------------------------------------------------------- cloture

    def test_close_rewrites_sections_and_links(self):
        code, out = self.run_script("--close", "1.5.0", "--date", "2026-10-12")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "liens"), "mis a jour")
        self.assertEqual(self.field(out, "notes"), "2 rubrique(s), 2 entree(s), identiques a la section close")
        text = self.changelog()
        self.assertIn("## [Non publié]\n\n## [1.5.0] - 2026-10-12\n\n### 🚀 Nouveautés", text)
        self.assertIn("[Non publié]: https://github.com/org/depot/compare/1.5.0...HEAD\n"
                      "[1.5.0]: https://github.com/org/depot/compare/1.4.1...1.5.0\n", text)

    def test_close_lowercase_label_crlf_and_v_prefix(self):
        self.set_repo(EN, tags=["v0.3.0"], newline="\r\n")
        code, out = self.run_script("--close", "0.3.1", "--date", "2026-10-12")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "liens"), "mis a jour")
        text = self.changelog()
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertIn("[unreleased]: https://github.com/org/depot/compare/v0.3.1...HEAD", text)
        self.assertIn("[0.3.1]: https://github.com/org/depot/compare/v0.3.0...v0.3.1", text)

    def test_close_keeps_v_in_headings(self):
        text = "# C\n\n## Unreleased\n\n### Fixed\n\n- x.\n\n## v1.0.0 - 2024-01-01\n\n### Added\n\n- a.\n"
        self.set_repo(text, tags=["v1.0.0"])
        code, out = self.run_script("--close", "1.0.1", "--date", "2026-10-12")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "liens"), "aucun")
        self.assertIn("## Unreleased\n\n## v1.0.1 - 2026-10-12\n", self.changelog())

    def test_close_postcondition_detects_lost_section(self):
        # Cas casse : la relecture du journal ecrit ne retrouve pas la version close.
        import importlib.util
        import unittest.mock
        spec = importlib.util.spec_from_file_location("journal_version", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cwd = os.getcwd()
        try:
            os.chdir(self.repo)
            with unittest.mock.patch.dict(os.environ, self.env), \
                    unittest.mock.patch.object(mod.Repo, "read", side_effect=[FR, FR]):
                code = mod.main(["--close", "1.5.0", "--date", "2026-10-12"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 1)

    def test_close_refuses_empty_section(self):
        self.set_repo(FR.replace("- Outil A.", "").replace("- Correction B.", ""), tags=["1.4.1"])
        before = self.changelog()
        code, out = self.run_script("--close", "1.5.0")
        self.assertEqual(code, 1, out)
        self.assertIn("sans entree", out)
        self.assertIn("CHANGELOG.md", out)
        self.assertEqual(self.changelog(), before)

    def test_close_refuses_without_unreleased_section(self):
        self.set_repo(FR.replace("## [Non publié]\n\n### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n", ""),
                      tags=["1.4.1"])
        code, out = self.run_script("--close", "1.5.0")
        self.assertEqual(code, 1, out)
        self.assertIn("n'est pas une section non publiee", out)

    def test_close_refuses_version_not_greater(self):
        self.assertIn("pas superieure", self.run_script("--close", "1.4.1")[1])
        # Un tag distant compte, meme absent du journal et des tags locaux.
        self.set_repo(FR, tags=["1.4.1"], remote=["1.6.0", "1.4.1"])
        code, out = self.run_script("--close", "1.6.0")
        self.assertEqual(code, 1, out)

    def test_close_refuses_bad_version_and_date(self):
        self.assertEqual(self.run_script("--close", "v1.5.0")[0], 1)
        self.assertEqual(self.run_script("--close", "1.5")[0], 1)
        self.assertEqual(self.run_script("--close", "1.5.0", "--date", "12/10/2026")[0], 1)

    # --------------------------------------------------------------- notes

    def test_notes_stdout_and_utf8_file(self):
        code, out = self.run_script("--notes", "1.4.1")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.strip(), "### 🐛 Corrections\n\n- Correction C.")
        target = self.dir / "RELEASE_NOTES.md"
        code, out = self.run_script("--notes", "1.4.1", "--output", str(target))
        self.assertEqual(code, 0, out)
        self.assertEqual(target.read_bytes().decode("utf-8"), "### 🐛 Corrections\n\n- Correction C.\n")
        self.assertNotIn("Correction C", out)
        self.assertEqual(self.run_script("--notes", "9.9.9")[0], 1)
        self.assertEqual(self.run_script("--output", str(target))[0], 1)

    def test_modes_are_exclusive(self):
        self.assertEqual(self.run_script("--close", "1.5.0", "--notes", "1.4.1")[0], 1)

    # -------------------------------------------------------------- check

    def check_fixtures(self, runs, tags=("1.4.1",), branch="main", head="h1", origin="h1"):
        empty = CLOSED.replace("### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n## [1.4.1]",
                               "## [1.4.1]", 1)
        empty = empty.replace("## [1.5.0] - 2026-10-12\n\n", "## [1.5.0] - 2026-10-12\n\n### 🚀 Nouveautés\n\n- Outil A.\n\n", 1)
        self.set_repo(empty, tags=list(tags), **{
            "git branch --show-current": ok(branch + "\n"),
            "git rev-parse HEAD": ok(head + "\n"),
            "git rev-parse refs/remotes/origin/main": ok(origin + "\n"),
            f"gh run list --commit {head} --json name,status,conclusion": ok(json.dumps(runs)),
        })

    def test_check_ready(self):
        self.check_fixtures([{"name": "CI", "status": "completed", "conclusion": "success"},
                             {"name": "lint", "status": "completed", "conclusion": "skipped"}])
        code, out = self.run_script("--check", "1.5.0")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "ci"), "2 succes, 0 echec, 0 en cours")
        self.assertEqual(self.field(out, "verdict"), "pret")
        self.assertEqual(self.field(out, "sha"), "h1")

    def test_check_blocks(self):
        # Cas casses : aucune execution, execution en cours, tag present, HEAD en retard.
        self.check_fixtures([])
        code, out = self.run_script("--check", "1.5.0")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.field(out, "ci"), "aucune execution")
        self.check_fixtures([{"name": "CI", "status": "in_progress", "conclusion": ""}])
        self.assertEqual(self.run_script("--check", "1.5.0")[0], 1)
        ok_runs = [{"name": "CI", "status": "completed", "conclusion": "success"}]
        self.check_fixtures(ok_runs, tags=("1.5.0", "1.4.1"))
        self.assertIn("le tag 1.5.0 existe deja", self.run_script("--check", "1.5.0")[1])
        self.check_fixtures(ok_runs, origin="h2")
        self.assertIn("HEAD differe de origin/main", self.run_script("--check", "1.5.0")[1])
        self.check_fixtures(ok_runs, branch="feat/x")
        self.assertIn("branche courante differente de main", self.run_script("--check", "1.5.0")[1])

    # ------------------------------------------------------------ release

    def test_release(self):
        self.workflow("release.yml", RELEASE_WF)
        self.set_repo(FR, tags=["1.4.1"], **{
            "git rev-list -n 1 1.4.1": ok("t1\n"),
            "gh run list --workflow release.yml --commit t1 --json status,conclusion":
                ok(json.dumps([{"status": "completed", "conclusion": "success"}])),
            "gh release view 1.4.1 --json url,isDraft": ok('{"url": "https://x/1.4.1", "isDraft": false}'),
        })
        code, out = self.run_script("--release", "1.4.1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "workflow"), "release.yml : success")
        self.assertEqual(self.field(out, "release"), "https://x/1.4.1")
        self.set_repo(FR, tags=["1.4.1"], **{
            "git rev-list -n 1 1.4.1": ok("t1\n"),
            "gh release view 1.4.1 --json url,isDraft": fail("release not found"),
        })
        self.assertEqual(self.field(self.run_script("--release", "1.4.1")[1], "release"), "absente")

    # --------------------------------------------------------- depot local

    def set_local(self, changelog, tags=(), shared=None, **over):
        """Depot sans origin : branche par defaut master, journal de master."""
        self.set_repo(changelog, tags=tags, remote=["1.4.1"], **{
            "git remote": ok(""),
            "git rev-parse --verify --quiet refs/heads/main": fail(),
            "git rev-parse --verify --quiet refs/heads/master": ok("m1\n"),
            "git show master:CHANGELOG.md": ok(changelog if shared is None else shared),
            **over})

    def test_local_state_uses_local_tags_and_base(self):
        # Cas casse : en mode distant, ls-remote (1.4.1 seul) donnerait l'etape tag.
        self.set_local(CLOSED, tags=["1.5.0", "1.4.1"])
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "distant"), "aucun (depot local)")
        self.assertEqual(self.field(out, "base"), "master")
        self.assertEqual(self.field(out, "etape"), "rien")
        self.set_local(CLOSED, tags=["1.4.1"])
        self.assertEqual(self.field(self.run_script()[1], "etape"), "tag (1.5.0, close sur master)")

    def test_local_step_waits_for_merge(self):
        self.set_local(CLOSED, tags=["1.4.1"], shared=FR)
        self.assertEqual(self.field(self.run_script()[1], "etape"),
                         "attente_merge (1.5.0, close localement, absente de master)")

    def test_local_check_without_origin_nor_ci(self):
        empty = CLOSED.replace("### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n## [1.4.1]",
                               "## [1.4.1]", 1)
        empty = empty.replace("## [1.5.0] - 2026-10-12\n\n", "## [1.5.0] - 2026-10-12\n\n### 🚀 Nouveautés\n\n- Outil A.\n\n", 1)
        self.set_local(empty, tags=["1.4.1"], **{
            "git branch --show-current": ok("master\n"), "git rev-parse HEAD": ok("h1\n")})
        code, out = self.run_script("--check", "1.5.0")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "ci"), "sans objet (depot local)")
        self.assertEqual(self.field(out, "verdict"), "pret")
        # Cas casse : verification lancee depuis la branche de travail.
        self.set_local(empty, tags=["1.4.1"], **{
            "git branch --show-current": ok("feat/x\n"), "git rev-parse HEAD": ok("h1\n")})
        self.assertIn("branche courante differente de master", self.run_script("--check", "1.5.0")[1])

    def tag_fixtures(self, kind="tag", contents="### 🐛 Corrections\n\n- Correction C.\n", ancestor=True):
        self.set_local(FR, tags=["1.4.1"], **{
            "git rev-list -n 1 1.4.1": ok("t1\n"),
            "git cat-file -t 1.4.1": ok(kind + "\n"),
            "git merge-base --is-ancestor t1 master": ok() if ancestor else fail(),
            "git tag -l --format=%(contents) 1.4.1": ok(contents)})

    def test_local_release_checks_tag(self):
        self.tag_fixtures()
        code, out = self.run_script("--release", "1.4.1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "verdict"), "conforme")
        self.tag_fixtures(contents="1.4.1\n\n### 🐛 Corrections\n\n- Correction C.\n")
        self.assertEqual(self.run_script("--release", "1.4.1")[0], 0)
        # Cas casses : tag leger, notes differentes, tag hors de la branche par defaut.
        self.tag_fixtures(kind="commit")
        code, out = self.run_script("--release", "1.4.1")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.field(out, "annote"), "non (tag leger)")
        self.tag_fixtures(contents="1.4.1\n")
        self.assertEqual(self.field(self.run_script("--release", "1.4.1")[1], "notes"), "differentes du journal")
        self.tag_fixtures(ancestor=False)
        self.assertTrue(self.field(self.run_script("--release", "1.4.1")[1], "sur_base").startswith("non"))

    def test_check_blocks_uncommitted_changes(self):
        # Cas casse : cloture ecrite dans la copie de travail, jamais committee.
        empty = CLOSED.replace("### 🚀 Nouveautés\n\n- Outil A.\n\n### 🐛 Corrections\n\n- Correction B.\n\n## [1.4.1]",
                               "## [1.4.1]", 1)
        empty = empty.replace("## [1.5.0] - 2026-10-12\n\n", "## [1.5.0] - 2026-10-12\n\n### 🚀 Nouveautés\n\n- Outil A.\n\n", 1)
        self.set_local(empty, tags=["1.4.1"], **{
            "git branch --show-current": ok("master\n"), "git rev-parse HEAD": ok("h1\n"),
            "git status --porcelain --untracked-files=no": ok(" M CHANGELOG.md\n")})
        code, out = self.run_script("--check", "1.5.0")
        self.assertEqual(code, 1, out)
        self.assertIn("modifications non committees : CHANGELOG.md", out)

    def test_remotes_without_origin_refused(self):
        self.set_repo(FR, tags=["1.4.1"], **{"git remote": ok("upstream\n")})
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("sans origin (upstream)", out)

    def test_notes_with_title(self):
        target = self.dir / "NOTES.md"
        code, out = self.run_script("--notes", "1.4.1", "--title", "1.4.1", "--output", str(target))
        self.assertEqual(code, 0, out)
        self.assertEqual(target.read_bytes().decode("utf-8"), "1.4.1\n\n### 🐛 Corrections\n\n- Correction C.\n")
        self.assertEqual(self.run_script("--title", "x")[0], 1)


if __name__ == "__main__":
    unittest.main()
