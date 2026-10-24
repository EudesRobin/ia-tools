#!/usr/bin/env python3
"""Tests de scripts/install.py sur une cible temporaire (--target), pour chaque
agent hote : installation sur cible vide, idempotence, etat par outil, conflit
sur edition locale sans ecriture de l'outil concerne, echec d'ecriture signale,
validation prealable bloquant 'apply', settings.json jamais ecrit ; audit court a
identifiants sans contenu de fichier, 'apply' par --all et --confirm,
identifiant perime refuse, 'view' et 'hunks' bornes (AGENTS.md, DoD des
scripts ; docs/SETUP.md).

Usage : python tests/test_install.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import contextlib
import difflib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ("claude", "copilot")

# Outil de plusieurs fichiers, distribue a chaque agent hote sous le meme chemin.
TOOL = "skills/clean-android-tv"
EDITED = f"{TOOL}/SKILL.md"
DELETED = f"{TOOL}/paquets.md"


def run_install(agent: str, target: Path, *options: str) -> tuple[int, dict]:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--agent", agent, "--target", str(target), "--json", *options],
        cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    try:
        report = json.loads(r.stdout)["agents"][agent]
    except (ValueError, KeyError):
        raise AssertionError(f"sortie --json illisible (code {r.returncode}) : {r.stdout}{r.stderr}")
    return r.returncode, report


def counts(report: dict) -> dict:
    return {status: len(sources) for status, sources in report["classes"].items()}


class TestInstall(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_target_then_idempotent(self):
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                code, r = run_install(agent, target, "apply", "--all")
                self.assertEqual(code, 0, r)
                self.assertTrue(r["ecrits"], f"{agent} : rien n'a ete ecrit")
                self.assertEqual(sorted(r["ecrits"]), sorted(r["classes"]["absent"]))
                self.assertEqual(r["echecs"], [])
                self.assertEqual(set(r["outils"].values()), {"installe"}, r["outils"])
                # Le chemin cible depend de l'agent hote (agent .md ou .agent.md) :
                # seul le nombre de fichiers presents est compare.
                present = [p for p in target.rglob("*") if p.is_file()]
                self.assertEqual(len(present), len(r["ecrits"]), f"{agent} : {present}")
                code, r = run_install(agent, target)
                self.assertEqual(code, 0, r)
                n = counts(r)
                self.assertGreater(n["identique"], 0)
                self.assertEqual(sum(v for k, v in n.items() if k != "identique"), 0, n)
                self.assertEqual(set(r["outils"].values()), {"a_jour"}, r["outils"])

    def test_conflict_blocks_tool(self):
        """--apply, obsolete, garde son comportement publie : un outil en conflit
        n'est pas ecrit."""
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                run_install(agent, target, "apply", "--all")
                edited, deleted = target / EDITED, target / DELETED
                self.assertTrue(edited.is_file() and deleted.is_file(), f"{agent} : {TOOL} non installe")
                edited.write_text("edition locale\n", encoding="utf-8")
                deleted.unlink()

                code, r = run_install(agent, target, "--apply")
                self.assertEqual(code, 1, f"{agent} : un conflit doit sortir en 1")
                self.assertIn(EDITED, r["classes"]["conflit"])
                self.assertIn("clean-android-tv", " ".join(r["outils_bloques"]))
                self.assertEqual(edited.read_text(encoding="utf-8"), "edition locale\n",
                                 f"{agent} : edition locale ecrasee")
                self.assertFalse(deleted.exists(), f"{agent} : fichier d'un outil bloque reecrit")
                self.assertNotIn(DELETED, r["ecrits"])
                self.assertEqual(r["outils"]["clean-android-tv"], "conflit")

    def test_write_failure_reported(self):
        """Une ecriture impossible est signalee et sort en 1, sans arreter les autres outils."""
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                (target / EDITED).mkdir(parents=True)  # un dossier a la place du fichier
                code, r = run_install(agent, target, "apply", "--all")
                self.assertEqual(code, 1, f"{agent} : un echec d'ecriture doit sortir en 1")
                self.assertIn(EDITED, r["echecs"])
                self.assertNotIn(EDITED, r["ecrits"])
                self.assertEqual(r["outils"]["clean-android-tv"], "echec")
                others = [s for s in r["ecrits"] if not s.startswith(TOOL + "/")]
                self.assertTrue(others, f"{agent} : les autres outils n'ont pas ete ecrits")

    def test_settings_json_never_written(self):
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                target.mkdir()
                settings = target / "settings.json"
                content = b'{\n  "model": "local"\n}\n'
                settings.write_bytes(content)
                code, r = run_install(agent, target, "apply", "--all")
                self.assertEqual(code, 0, r)
                self.assertEqual(settings.read_bytes(), content, f"{agent} : settings.json modifie")


    def test_tool_option_and_deprecated_alias(self):
        """--tool restreint l'installation ; --outil reste accepte et avertit."""
        for option, warns in (("--tool", False), ("--outil", True)):
            with self.subTest(option):
                target = self.tmp / option.strip("-")
                r = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "install.py"), "--agent", "claude",
                     "--target", str(target), option, "clean-android-tv", "apply", "--all", "--json"],
                    cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                )
                self.assertEqual(r.returncode, 0, r.stderr)
                written = json.loads(r.stdout)["agents"]["claude"]["ecrits"]
                self.assertTrue(written)
                self.assertTrue(all(s.startswith(TOOL + "/") for s in written), written)
                self.assertEqual("obsolete" in r.stderr, warns, r.stderr)

    def test_validation_gates_apply(self):
        """Validateur en echec : 'apply' n'ecrit rien ; anomalie d'environnement : avertit."""
        spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
        install = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install)
        for exit_code, expected, writes in ((1, 1, False), (2, 0, True)):
            with self.subTest(exit_code):
                validator = self.tmp / f"validator_{exit_code}.py"
                validator.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")
                target = self.tmp / f"target_{exit_code}"
                install.VALIDATOR = validator
                argv = ["install.py", "--agent", "claude", "--target", str(target), "apply", "--all"]
                out = io.StringIO()
                with unittest.mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
                    code = install.main()
                self.assertEqual(code, expected, out.getvalue())
                self.assertEqual(target.exists() and any(target.rglob("*")), writes, out.getvalue())
                self.assertIn("validation", out.getvalue())


    def test_tool_adds_declared_dependencies(self):
        """--tool installe aussi les dependances declarees, et les signale."""
        spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
        install = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install)
        validator = self.tmp / "validator_ok.py"
        validator.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        readme = self.tmp / "README.md"
        readme.write_text(DEPS_README.format(tool="clean-android-tv", dep="setup-harness"), encoding="utf-8")
        install.VALIDATOR = validator
        install.DEPENDENCIES_FILE = readme
        target = self.tmp / "cible"
        argv = ["install.py", "--agent", "claude", "--target", str(target),
                "--tool", "clean-android-tv", "apply", "--all", "--json"]
        out = io.StringIO()
        with unittest.mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            code = install.main()
        self.assertEqual(code, 0, out.getvalue())
        report = json.loads(out.getvalue())
        self.assertEqual(report["dependances_ajoutees"], ["setup-harness"])
        written = report["agents"]["claude"]["ecrits"]
        self.assertTrue(any(s.startswith("skills/setup-harness/") for s in written), written)
        self.assertTrue(any(s.startswith(TOOL + "/") for s in written), written)


def run_text(agent: str, target: Path, *options: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--agent", agent, "--target", str(target), *options],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )


def actions_of(target: Path, agent: str = "claude") -> list[dict]:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--agent", agent, "--target", str(target), "--json"],
        cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    return json.loads(r.stdout)["actions"]


def view_path(stdout: str, label: str) -> Path:
    """Chemin d'une ligne '  <label> : <chemin>' de la sortie de 'view'."""
    line = next(l for l in stdout.splitlines() if l.startswith(f"  {label} : "))
    return Path(line.split(" : ", 1)[1].strip())


# Les assertions sur le contenu d'un fichier portent un message court : un
# echec ne doit pas recopier le fichier dans la sortie.

# Fichier de plus de 500 lignes portant un placeholder {AGENT_DIR}.
BIG = f"{TOOL}/reference-adb.md"


class TestAuditApply(unittest.TestCase):
    """audit court a identifiants, apply par --all et --confirm, view et hunks
    sans contenu dans la sortie standard."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.target = self.tmp / "claude"
        run_install("claude", self.target, "apply", "--all")
        self.big = self.target / BIG
        lines = self.big.read_text(encoding="utf-8").splitlines(True)
        self.assertGreater(len(lines), 500)
        lines[10] = "ligne editee a la main, marqueur-local\n"
        self.local = "".join(lines)
        self.big.write_text(self.local, encoding="utf-8")
        (self.target / DELETED).unlink()

    def tearDown(self):
        self._tmp.cleanup()

    def conflict(self) -> dict:
        found = [a for a in actions_of(self.target) if a["type"] == "conflit"]
        self.assertEqual([a["chemin"] for a in found], [BIG])
        return found[0]

    def test_audit_is_short_and_without_content(self):
        r = run_text("claude", self.target)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertLessEqual(len(r.stdout.splitlines()), 15, r.stdout)
        self.assertNotIn("marqueur-local", r.stdout)
        self.assertIn(self.conflict()["id"], r.stdout)
        self.assertIn("local : 1 bloc(s) l.11 ; depot : 0 bloc(s) ; fusionnable", r.stdout)

    def test_hunks_bounded_and_view_without_content(self):
        ident = self.conflict()["id"]
        r = run_text("claude", self.target, "hunks", ident, "--max-lines", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = r.stdout.splitlines()
        # En-tete, deux lignes de diff (@@ et la ligne locale), mention de la coupure.
        self.assertEqual(len(body), 4, r.stdout)
        self.assertIn("marqueur-local", body[2])
        self.assertIn("non affichee", body[3])
        r = run_text("claude", self.target, "view", ident)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("marqueur-local", r.stdout)
        text = view_path(r.stdout, "depot").read_text(encoding="utf-8")
        self.assertFalse("marqueur-local" in text, "edition locale dans la version du depot")
        self.assertFalse("{AGENT_DIR}" in text, "placeholder non substitue")

    def test_conflict_requires_choice_and_fresh_id(self):
        ident = self.conflict()["id"]
        for confirm in (ident, f"{ident}=autre", "0000=depot"):
            with self.subTest(confirm):
                r = run_text("claude", self.target, "apply", "--confirm", confirm)
                self.assertEqual(r.returncode, 1)
                self.assertIn("rien n'est ecrit", r.stderr)
                self.assertEqual(self.big.read_text(encoding="utf-8"), self.local)
                self.assertFalse((self.target / DELETED).exists())
        # Cible modifiee apres l'audit : l'identifiant est perime.
        self.big.write_text(self.local + "autre edition\n", encoding="utf-8")
        r = run_text("claude", self.target, "apply", "--confirm", f"{ident}=depot")
        self.assertIn("perime", r.stderr)
        self.assertTrue(self.big.read_text(encoding="utf-8").endswith("autre edition\n"))

    def test_confirm_depot_backs_up_and_unblocks_tool(self):
        ident = self.conflict()["id"]
        code, r = run_install("claude", self.target, "apply", "--confirm", f"{ident}=depot")
        self.assertEqual(code, 0, r)
        self.assertEqual(r["resolus"], [BIG])
        self.assertNotIn("marqueur-local", self.big.read_text(encoding="utf-8"))
        self.assertTrue((self.target / DELETED).is_file(), "outil debloque non complete")
        saved = Path(r["sauvegarde"]) / BIG
        self.assertEqual(saved.read_text(encoding="utf-8"), self.local)
        self.assertEqual(actions_of(self.target), [])

    def test_confirm_local_keeps_file_and_unblocks_tool(self):
        ident = self.conflict()["id"]
        code, r = run_install("claude", self.target, "apply", "--confirm", f"{ident}=local")
        self.assertEqual(code, 1, "un conflit garde en local reste un conflit")
        self.assertEqual(self.big.read_text(encoding="utf-8"), self.local)
        self.assertTrue((self.target / DELETED).is_file(), "outil arbitre non complete")
        self.assertIsNone(r["sauvegarde"])

    def test_confirm_one_update_only(self):
        other = self.tmp / "autre"
        run_install("claude", other, "apply", "--all")
        for rel in (DELETED, "skills/release/SKILL.md"):
            (other / rel).unlink()
        maj = {a["outil"]: a["id"] for a in actions_of(other) if a["type"] == "maj"}
        self.assertEqual(set(maj), {"clean-android-tv", "release"}, maj)
        code, r = run_install("claude", other, "apply", "--confirm", maj["release"])
        self.assertEqual(code, 0, r)
        self.assertEqual(r["ecrits"], ["skills/release/SKILL.md"])
        self.assertFalse((other / DELETED).exists())

    def test_raw_copy_is_obsolete(self):
        """Une copie manuelle, placeholders non substitues, n'est pas un conflit."""
        other = self.tmp / "copie"
        run_install("claude", other, "apply", "--all")
        (other / BIG).write_bytes((ROOT / BIG).read_bytes())
        code, r = run_install("claude", other)
        self.assertEqual(code, 0, r)
        self.assertIn(BIG, r["classes"]["obsolete"])

    def test_apply_needs_selection_and_alias_warns(self):
        r = run_text("claude", self.tmp / "vide", "apply")
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.tmp / "vide").exists())
        r = run_text("claude", self.tmp / "alias", "--apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("obsolete", r.stderr)
        self.assertTrue((self.tmp / "alias" / DELETED).is_file())


def load_install():
    spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MARKER = "ligne editee a la main, marqueur-local\n"


class TestFusion(unittest.TestCase):
    """Base du merge tiree de l'historique, verdict fusionnable, choix fusion et
    fichier, version du depot adoptee par defaut avec --all."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.target = self.tmp / "claude"
        run_install("claude", self.target, "apply", "--all")
        install = load_install()
        subs = install.variables("claude", self.target.resolve(), True)
        self.current = install.normalize((self.target / BIG).read_bytes()).decode("utf-8")
        # Une revision anterieure du fichier, differente de la version du depot.
        old = next(r for r in install.previous_renders(BIG, subs) if r.decode("utf-8") != self.current)
        self.old_lines = old.decode("utf-8").splitlines(True)
        self.ops = [
            op for op in difflib.SequenceMatcher(
                None, self.old_lines, self.current.splitlines(True), autojunk=False
            ).get_opcodes() if op[0] != "equal"
        ]

    def tearDown(self):
        self._tmp.cleanup()

    def edit_old_revision(self, index: int) -> str:
        """Cible : la revision anterieure, editee a la ligne index."""
        lines = list(self.old_lines)
        lines[index] = MARKER
        local = "".join(lines)
        (self.target / BIG).write_bytes(local.encode("utf-8"))
        return local

    def disjoint_index(self) -> int:
        near = {i for _, i1, i2, _, _ in self.ops for i in range(i1 - 3, i2 + 3)}
        return next(i for i, line in enumerate(self.old_lines) if i not in near and line.strip())

    def overlap_index(self) -> int:
        return next(i1 for tag, i1, _, _, _ in self.ops if tag == "replace")

    def conflict(self) -> dict:
        found = [a for a in actions_of(self.target) if a["type"] == "conflit"]
        self.assertEqual([a["chemin"] for a in found], [BIG])
        return found[0]

    def test_disjoint_edit_merged(self):
        index = self.disjoint_index()
        local = self.edit_old_revision(index)
        action = self.conflict()
        self.assertTrue(action["fusionnable"], action)
        self.assertIn("fusion", action["choix"])
        code, r = run_install("claude", self.target, "apply", "--confirm", f"{action['id']}=fusion")
        self.assertEqual(r["resolus"], [BIG])
        merged = (self.target / BIG).read_bytes().decode("utf-8").replace("\r\n", "\n")
        # Edition locale conservee, evolutions du depot reportees.
        self.assertTrue(merged.replace(MARKER, self.old_lines[index]) == self.current,
                        "merge different de la version du depot plus l'edition locale")
        saved = (Path(r["sauvegarde"]) / BIG).read_text(encoding="utf-8")
        self.assertTrue(saved == local, "sauvegarde differente de la version locale")
        self.assertEqual(code, 1, "une edition locale gardee reste un conflit")
        self.assertIn("deja a jour du depot", self.conflict()["resume"])

    def test_all_adopts_repo_version_by_default(self):
        local = self.edit_old_revision(self.disjoint_index())
        code, r = run_install("claude", self.target, "apply", "--all")
        self.assertEqual(code, 0, r)
        self.assertEqual(r["resolus"], [BIG])
        got = (self.target / BIG).read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertTrue(got == self.current, "version du depot non adoptee")
        saved = (Path(r["sauvegarde"]) / BIG).read_text(encoding="utf-8")
        self.assertTrue(saved == local, "sauvegarde differente de la version locale")
        self.assertEqual(actions_of(self.target), [])

    def test_overlap_refuses_fusion_and_hunks_shows_zones(self):
        self.edit_old_revision(self.overlap_index())
        action = self.conflict()
        self.assertFalse(action["fusionnable"])
        self.assertNotIn("fusion", action["choix"])
        self.assertIn("zone(s) en chevauchement", action["resume"])
        r = run_text("claude", self.target, "apply", "--confirm", f"{action['id']}=fusion")
        self.assertEqual(r.returncode, 1)
        self.assertIn("rien n'est ecrit", r.stderr)
        r = run_text("claude", self.target, "hunks", action["id"], "--max-lines", "3")
        body = r.stdout.splitlines()[1:]
        self.assertTrue(body and body[0].startswith("<<<<<<< local"), "zone en chevauchement absente")
        self.assertLessEqual(len(body), 4)  # trois lignes et la mention de la coupure

    def test_corrected_merge_file(self):
        self.edit_old_revision(self.overlap_index())
        ident = self.conflict()["id"]
        r = run_text("claude", self.target, "apply", "--confirm", f"{ident}=fichier")
        self.assertIn("view", r.stderr, "fichier exige d'abord 'view'")
        r = run_text("claude", self.target, "view", ident)
        self.assertNotIn("marqueur-local", r.stdout)
        merge_file = view_path(r.stdout, "merge")
        self.assertTrue("<<<<<<<" in merge_file.read_text(encoding="utf-8"), "merge sans marqueur")
        r = run_text("claude", self.target, "apply", "--confirm", f"{ident}=fichier")
        self.assertIn("marqueurs", r.stderr)
        merge_file.write_text("contenu corrige\n", encoding="utf-8")
        code, r = run_install("claude", self.target, "apply", "--confirm", f"{ident}=fichier")
        self.assertEqual(r["resolus"], [BIG])
        got = (self.target / BIG).read_text(encoding="utf-8")
        self.assertTrue(got == "contenu corrige\n", "fichier corrige non ecrit")


class TestDependencies(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
        self.install = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.install)

    def test_declared_dependencies(self):
        text = DEPS_README.format(tool="a", dep="b") + "| [`a`](x) | `c`, `b` | y |\n\n## Suite\n| [`z`](x) | `w` | hors section |\n"
        self.assertEqual(self.install.declared_dependencies(text), {"a": ["b", "c"]})
        self.assertEqual(self.install.declared_dependencies("# Sans carte\n"), {})
        empty = "## Dépendances entre outils\n\n| Outil | Dépend de | Pour |\n|---|---|---|\n"
        self.assertEqual(self.install.declared_dependencies(empty), {})

    def test_with_dependencies_transitive_and_cycle(self):
        deps = {"a": ["b"], "b": ["c", "a"], "c": []}
        self.assertEqual(self.install.with_dependencies({"a"}, deps), {"a", "b", "c"})
        self.assertEqual(self.install.with_dependencies({"c"}, deps), {"c"})


DEPS_README = (
    "# Depot\n\n## Dépendances entre outils\n\n| Outil | Dépend de | Pour |\n|---|---|---|\n"
    "| [`{tool}`](x) | `{dep}` | essai |\n"
)


if __name__ == "__main__":
    unittest.main(verbosity=2)
