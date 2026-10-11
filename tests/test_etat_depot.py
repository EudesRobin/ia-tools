#!/usr/bin/env python3
"""Tests de skills/pull-request/etat_depot.py, sans depot GitHub : un faux git
et un faux gh renvoient des sorties enregistrees et journalisent leurs appels.
Chaque garde-fou sur les donnees sensibles est vu en rouge sur un cas
volontairement casse (AGENTS.md, DoD des scripts).

Usage : python tests/test_etat_depot.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "pull-request" / "etat_depot.py"

FAKE = '''
import json, os, sys
tool = TOOL
key = " ".join([tool, *sys.argv[1:]])
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(key + "\\n")
fixtures = json.load(open(os.environ["FAKE_FIXTURES"], encoding="utf-8"))
entry = fixtures.get(key, {"code": 1, "err": "commande non prevue : " + key})
sys.stdout.write(entry.get("out", ""))
sys.stderr.write(entry.get("err", ""))
sys.exit(entry.get("code", 0))
'''

TOKEN = "gho_FAUXJETON0123456789"


def ok(out=""):
    return {"code": 0, "out": out}


def fail(err="", code=1):
    return {"code": code, "err": err}


def load_module():
    spec = importlib.util.spec_from_file_location("etat_depot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EtatDepotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.repo = self.dir / "depot"
        (self.repo / ".git" / "hooks").mkdir(parents=True)
        self.git = self.dir / "fake_git.py"
        self.gh = self.dir / "fake_gh.py"
        self.git.write_text(FAKE.replace("TOOL", '"git"'), encoding="utf-8")
        self.gh.write_text(FAKE.replace("TOOL", '"gh"'), encoding="utf-8")
        self.log = self.dir / "calls.log"
        self.fixtures(self.base_fixtures())

    def tearDown(self):
        self.tmp.cleanup()

    def base_fixtures(self, **over):
        f = {
            "git rev-parse --absolute-git-dir": ok(f"{(self.repo / '.git').as_posix()}\n"),
            "git rev-parse --show-toplevel": ok(f"{self.repo.as_posix()}\n"),
            "git branch --show-current": ok("feat/essai\n"),
            "git remote": ok("origin\n"),
            "git symbolic-ref --short refs/remotes/origin/HEAD": ok("origin/main\n"),
            "git rev-parse --verify --quiet HEAD": ok("abc123\n"),
            "git rev-parse --abbrev-ref --symbolic-full-name @{u}": fail("no upstream", 128),
            "git rev-parse --verify --quiet refs/remotes/origin/main": ok("def456\n"),
            "git rev-list --count origin/main..HEAD": ok("2\n"),
            "git status --porcelain=v1 --untracked-files=all": ok(" M src/a.py\nA  src/b.py\n?? notes.txt\n"),
            "git config core.hooksPath": fail(),
            "gh auth status": ok(f"Logged in to github.com\n  - Token: {TOKEN}\n"),
            "gh repo view --json nameWithOwner,defaultBranchRef":
                ok(json.dumps({"nameWithOwner": "org/depot", "defaultBranchRef": {"name": "main"}})),
            "gh pr view --json number,url,state,baseRefName":
                fail("no pull requests found for branch \"feat/essai\"\n"),
        }
        f.update(over)
        return f

    def fixtures(self, data):
        path = self.dir / "fixtures.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        self.env = {**os.environ, "FAKE_FIXTURES": str(path), "FAKE_LOG": str(self.log),
                    "PYTHONUTF8": "1"}

    def run_script(self, *args, gh=None):
        res = subprocess.run(
            [sys.executable, str(SCRIPT), "--git", str(self.git), "--gh", str(gh or self.gh), *args],
            capture_output=True, text=True, env=self.env, encoding="utf-8", cwd=self.repo,
        )
        return res.returncode, res.stdout + res.stderr

    def calls(self):
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def field(self, out, key):
        for line in out.splitlines():
            name, _, value = line.partition(" : ")
            if name.strip() == key:
                return value
        self.fail(f"champ {key} absent :\n{out}")

    # ---------------------------------------------------------- commit seul

    def test_commit_only_never_calls_gh(self):
        code, out = self.run_script(gh=self.dir / "absent.py")
        self.assertEqual(code, 0, out)
        self.assertFalse([c for c in self.calls() if c.startswith("gh ")])
        self.assertEqual(self.field(out, "branche"), "feat/essai")
        self.assertEqual(self.field(out, "base"), "main (origin/HEAD)")
        self.assertEqual(self.field(out, "a_pousser"), "2 (sur origin/main)")
        self.assertEqual(self.field(out, "avance_sur_base"), "2 (sur origin/main)")
        self.assertEqual(self.field(out, "modifications"),
                         "1 indexee(s), 1 non indexee(s), 1 non suivie(s)")
        self.assertEqual(self.field(out, "git_dir"), (self.repo / ".git").as_posix())
        self.assertLess(len(out.splitlines()), 20, "sortie trop longue")

    def test_upstream_takes_precedence(self):
        self.fixtures(self.base_fixtures(**{
            "git rev-parse --abbrev-ref --symbolic-full-name @{u}": ok("origin/feat/essai\n"),
            "git rev-list --count origin/feat/essai..HEAD": ok("0\n"),
        }))
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "a_pousser"), "0 (sur origin/feat/essai)")

    def test_repository_without_remote(self):
        self.fixtures(self.base_fixtures(**{
            "git remote": ok(""),
            "git rev-parse --verify --quiet refs/heads/main": fail(),
            "git rev-parse --verify --quiet refs/heads/master": ok("aaa\n"),
            "git rev-list --count master..HEAD": ok("1\n"),
        }))
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "distants"), "aucun")
        self.assertTrue(self.field(out, "base").startswith("master (branche locale"))
        self.assertTrue(self.field(out, "a_pousser").startswith("sans objet"))
        self.assertEqual(self.field(out, "avance_sur_base"), "1 (sur master)")

    def test_not_a_repository_is_environment_error(self):
        self.fixtures(self.base_fixtures(**{
            "git rev-parse --absolute-git-dir": fail("fatal: not a git repository", 128),
            "git rev-parse --show-toplevel": fail("fatal: not a git repository", 128),
        }))
        code, out = self.run_script()
        self.assertEqual(code, 2, out)

    def test_usage_error_exits_1(self):
        code, out = self.run_script("--inconnue")
        self.assertEqual(code, 1, out)

    # ------------------------------------------------------- conventions

    def test_detects_conventions_hooks_and_templates(self):
        for rel in ("AGENTS.md", "docs/CONTRIBUTING.md", "commitlint.config.js",
                    ".githooks/commit-msg", ".github/PULL_REQUEST_TEMPLATE/bug.md",
                    ".github/PULL_REQUEST_TEMPLATE/feature.md"):
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
        self.fixtures(self.base_fixtures(**{"git config core.hooksPath": ok(".githooks\n")}))
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "conventions"), "AGENTS.md, docs/CONTRIBUTING.md")
        self.assertEqual(self.field(out, "hooks_path"), ".githooks")
        self.assertEqual(self.field(out, "hook_commit_msg"), "present")
        self.assertEqual(self.field(out, "commitlint"), "commitlint.config.js")
        self.assertEqual(self.field(out, "templates_pr"),
                         ".github/PULL_REQUEST_TEMPLATE/bug.md, .github/PULL_REQUEST_TEMPLATE/feature.md")

    def test_sample_hook_is_not_a_hook(self):
        (self.repo / ".git" / "hooks" / "commit-msg.sample").write_text("x", encoding="utf-8")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "hook_commit_msg"), "absent")
        self.assertEqual(self.field(out, "templates_pr"), "aucun")

    # -------------------------------------------------- donnees sensibles

    def test_sensitive_files_named_and_excluded(self):
        self.fixtures(self.base_fixtures(**{
            "git status --porcelain=v1 --untracked-files=all":
                ok(" M .env\n?? config/prod.pem\n?? .env.example\nR  old.txt -> keys/id_ed25519\n M src/a.py\n"),
        }))
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "sensibles"), ".env, config/prod.pem, keys/id_ed25519")
        self.assertEqual(self.field(out, "exclusions_diff"),
                         "':(exclude).env' ':(exclude)config/prod.pem' ':(exclude)keys/id_ed25519'")

    def test_no_exclusion_line_without_sensitive_file(self):
        code, out = self.run_script()
        self.assertEqual(self.field(out, "sensibles"), "aucun")
        self.assertNotIn("exclusions_diff", out)

    def test_remote_url_and_token_never_requested(self):
        code, out = self.run_script("--github")
        self.assertEqual(code, 0, out)
        calls = self.calls()
        self.assertIn("git remote", calls)
        self.assertFalse([c for c in calls if c.startswith("git remote ")], calls)
        self.assertFalse([c for c in calls if "token" in c.lower()], calls)
        self.assertNotIn(TOKEN, out)

    def test_auth_failure_hides_gh_output(self):
        self.fixtures(self.base_fixtures(**{
            "gh auth status": fail(f"You are not logged in\n  - Token: {TOKEN}\n"),
        }))
        code, out = self.run_script("--github")
        self.assertEqual(code, 2, out)
        self.assertIn("gh auth login", out)
        self.assertNotIn(TOKEN, out)

    # ------------------------------------------------------------- GitHub

    def test_github_existing_pr(self):
        pr = {"number": 12, "url": "https://github.com/org/depot/pull/12",
              "state": "OPEN", "baseRefName": "main"}
        self.fixtures(self.base_fixtures(**{
            "gh pr view --json number,url,state,baseRefName": ok(json.dumps(pr)),
        }))
        code, out = self.run_script("--github")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "base"), "main (depot GitHub)")
        self.assertEqual(self.field(out, "depot_github"), "org/depot")
        self.assertEqual(self.field(out, "pr"), "#12 OPEN base=main https://github.com/org/depot/pull/12")

    def test_github_without_pr(self):
        code, out = self.run_script("--github")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "pr"), "aucune")

    def test_github_unexpected_pr_error_is_reported(self):
        self.fixtures(self.base_fixtures(**{
            "gh pr view --json number,url,state,baseRefName": fail("HTTP 502: Bad Gateway\n"),
        }))
        code, out = self.run_script("--github")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "pr"), "indeterminee (HTTP 502: Bad Gateway)")

    def test_github_requested_but_gh_missing(self):
        code, out = self.run_script("--github", gh=self.dir / "absent.py")
        self.assertEqual(code, 2, out)
        self.assertIn("gh introuvable", out)

    # ---------------------------------------------------------- post-merge

    FOR_EACH_REF = "git for-each-ref refs/heads --format=%(refname:lstrip=2) %(objectname)"
    PR_LIST = "gh pr list --state merged --limit 100 --json number,headRefName,headRefOid"

    def post_merge_fixtures(self, **over):
        main = self.repo.as_posix()
        self.tree = self.dir / "arbre-b"
        self.tree.mkdir(exist_ok=True)
        tree = self.tree.as_posix()
        f = self.base_fixtures(**{
            "git worktree list --porcelain": ok(
                f"worktree {main}\nHEAD aaa111\nbranch refs/heads/feat/a\n\n"
                f"worktree {tree}\nHEAD bbb222\nbranch refs/heads/feat/b\n\n"),
            f"git -C {main} status --porcelain=v1 --untracked-files=all": ok(""),
            f"git -C {main} log -1 --format=%h %s": ok("aaa111 feat: sujet\n"),
            f"git -C {tree} status --porcelain=v1 --untracked-files=all --ignored": ok(""),
            self.FOR_EACH_REF: ok(
                "feat/a aaa111\nfeat/b bbb222\nfeat/c ccc333\nfeat/d ddd444\nmain mmm000\n"),
            self.PR_LIST: ok(json.dumps([
                {"number": 42, "headRefName": "feat/a", "headRefOid": "aaa111"},
                {"number": 41, "headRefName": "feat/b", "headRefOid": "bbb222"},
                {"number": 40, "headRefName": "feat/c", "headRefOid": "cccPR40ffff"},
            ])),
            "git cat-file -e cccPR40ffff^{commit}": fail(),
        })
        f.update(over)
        return f

    def fields(self, out, key):
        return [v for k, _, v in (l.partition(" : ") for l in out.splitlines()) if k.strip() == key]

    def test_post_merge_classifies_branches(self):
        self.fixtures(self.post_merge_fixtures())
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "base"), "main")
        self.assertEqual(self.field(out, "worktree_courant"), "principal")
        self.assertEqual(self.field(out, "branche"), "feat/a")
        self.assertEqual(self.field(out, "dernier_commit"), "aaa111 feat: sujet")
        self.assertEqual(self.fields(out, "mergee"), [
            "feat/a #42 head=identique worktree=aucun",
            f"feat/b #41 head=identique worktree={self.tree.as_posix()} etat=propre",
            "feat/c #40 head=divergente pr_head=cccPR40 commits_locaux=indetermine worktree=aucun",
        ])
        self.assertEqual(self.field(out, "non_mergees"), "feat/d")
        self.assertNotIn("base_extraite", out)
        self.assertLess(len(out.splitlines()), 20, "sortie trop longue")

    def test_post_merge_diverging_head_never_deletable(self):
        # Cas casse : le head local porte un commit absent de la PR mergee.
        self.fixtures(self.post_merge_fixtures(**{
            self.FOR_EACH_REF: ok("feat/a fff999\n"),
            "git cat-file -e aaa111^{commit}": ok(),
            "git merge-base --is-ancestor fff999 aaa111": fail(),
            "git rev-list --count aaa111..refs/heads/feat/a": ok("2\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fields(out, "mergee"),
                         ["feat/a #42 head=divergente pr_head=aaa111 commits_locaux=2 worktree=aucun"])
        self.assertNotIn("identique", out)

    def test_post_merge_head_behind_pr_is_not_identical(self):
        self.fixtures(self.post_merge_fixtures(**{
            self.FOR_EACH_REF: ok("feat/a eee888\n"),
            "git cat-file -e aaa111^{commit}": ok(),
            "git merge-base --is-ancestor eee888 aaa111": ok(),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fields(out, "mergee"), ["feat/a #42 head=en_retard pr_head=aaa111 worktree=aucun"])

    def test_post_merge_matches_older_pr_of_same_branch(self):
        self.fixtures(self.post_merge_fixtures(**{
            self.PR_LIST: ok(json.dumps([
                {"number": 50, "headRefName": "feat/a", "headRefOid": "zzz000"},
                {"number": 42, "headRefName": "feat/a", "headRefOid": "aaa111"},
            ])),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertIn("feat/a #42 head=identique worktree=aucun", self.fields(out, "mergee"))

    def test_post_merge_worktree_states(self):
        tree = (self.dir / "arbre-b").as_posix()
        self.fixtures(self.post_merge_fixtures(**{
            f"git -C {tree} status --porcelain=v1 --untracked-files=all --ignored":
                ok(" M a.py\n?? b.txt\n!! .env\n!! build/\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertIn(f"feat/b #41 head=identique worktree={tree} etat=modifie:2,ignores:2",
                      self.fields(out, "mergee"))

    def test_post_merge_ignored_files_only(self):
        # Cas casse : seuls des fichiers ignores, que git worktree remove supprime sans avertir.
        tree = (self.dir / "arbre-b").as_posix()
        self.fixtures(self.post_merge_fixtures(**{
            f"git -C {tree} status --porcelain=v1 --untracked-files=all --ignored": ok("!! .env\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertIn(f"worktree={tree} etat=ignores:1", "\n".join(self.fields(out, "mergee")))

    def test_post_merge_locked_and_missing_worktrees(self):
        main, tree = self.repo.as_posix(), (self.dir / "arbre-b").as_posix()
        gone = (self.dir / "disparu").as_posix()
        self.fixtures(self.post_merge_fixtures(**{
            "git worktree list --porcelain": ok(
                f"worktree {main}\nHEAD aaa111\nbranch refs/heads/feat/a\n\n"
                f"worktree {tree}\nHEAD bbb222\nbranch refs/heads/feat/b\nlocked\n\n"
                f"worktree {gone}\nHEAD ccc333\nbranch refs/heads/feat/c\nprunable gitdir file points to non-existent location\n\n"),
            "git cat-file -e cccPR40ffff^{commit}": fail(),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        merged = "\n".join(self.fields(out, "mergee"))
        self.assertIn(f"worktree={tree} etat=verrouille", merged)
        self.assertIn(f"worktree={gone} etat=absent", merged)

    def test_post_merge_from_linked_worktree(self):
        tree = self.dir / "arbre-b"
        self.fixtures(self.post_merge_fixtures(**{
            "git rev-parse --show-toplevel": ok(f"{tree.as_posix()}\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "worktree_courant"), "lie")
        self.assertEqual(self.field(out, "racine_principale"), self.repo.as_posix())
        # Modifications et branche relevees dans le worktree principal.
        self.assertEqual(self.field(out, "branche"), "feat/a")

    def test_post_merge_detached_head_and_base_checked_out_elsewhere(self):
        main, tree = self.repo.as_posix(), (self.dir / "arbre-b").as_posix()
        self.fixtures(self.post_merge_fixtures(**{
            "git worktree list --porcelain": ok(
                f"worktree {main}\nHEAD aaa111\ndetached\n\n"
                f"worktree {tree}\nHEAD mmm000\nbranch refs/heads/main\n\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "branche"), "(HEAD detachee)")
        self.assertEqual(self.field(out, "base_extraite"), tree)

    def test_post_merge_reports_uncommitted_changes(self):
        main = self.repo.as_posix()
        self.fixtures(self.post_merge_fixtures(**{
            f"git -C {main} status --porcelain=v1 --untracked-files=all": ok(" M src/a.py\n"),
        }))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.field(out, "modifications"),
                         "0 indexee(s), 1 non indexee(s), 0 non suivie(s)")

    def test_post_merge_requires_gh(self):
        code, out = self.run_script("--post-merge", gh=self.dir / "absent.py")
        self.assertEqual(code, 2, out)
        self.assertIn("gh introuvable", out)

    def test_post_merge_pr_list_failure_is_environment_error(self):
        self.fixtures(self.post_merge_fixtures(**{self.PR_LIST: fail("HTTP 502\n")}))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 2, out)
        self.assertNotIn("mergee", out)

    def test_post_merge_unreadable_json_is_environment_error(self):
        self.fixtures(self.post_merge_fixtures(**{self.PR_LIST: ok("<html>erreur</html>")}))
        code, out = self.run_script("--post-merge")
        self.assertEqual(code, 2, out)
        self.assertIn("sortie JSON illisible", out)
        self.assertNotIn("Traceback", out)

    def test_post_merge_excludes_github(self):
        code, out = self.run_script("--post-merge", "--github")
        self.assertEqual(code, 1, out)


class UnitTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()

    def test_is_sensitive(self):
        for name in (".env", "a/.env.local", "x.pem", "srv.key", "id_rsa", "aws_credentials", ".netrc"):
            self.assertTrue(self.mod.is_sensitive(name), name)
        for name in (".env.example", "keys.md", "src/env.py", "README.md", "credentials.sample"):
            self.assertFalse(self.mod.is_sensitive(name), name)

    def test_parse_porcelain(self):
        staged, unstaged, untracked, paths = self.mod.parse_porcelain(
            "MM a.py\nR  b.py -> c.py\n?? d.txt\n D e.py\n")
        self.assertEqual((staged, unstaged, untracked), (2, 2, 1))
        self.assertEqual(paths, ["a.py", "c.py", "d.txt", "e.py"])

    def test_parse_worktrees(self):
        found = self.mod.parse_worktrees(
            "worktree /d/nu\nbare\n\n"
            "worktree /d/main\nHEAD a\nbranch refs/heads/main\n\n"
            "worktree /d/wt\nHEAD b\ndetached\nlocked raison\n\n")
        self.assertEqual([(t["path"].as_posix(), t["branch"], t["locked"]) for t in found],
                         [("/d/main", "main", False), ("/d/wt", None, True)])


if __name__ == "__main__":
    unittest.main()
