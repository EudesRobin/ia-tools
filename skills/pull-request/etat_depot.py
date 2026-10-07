#!/usr/bin/env python3
"""Etat du depot git pour la skill pull-request, en lecture seule.

Lance la sequence fixe des commandes git (et gh avec --github), repere les
fichiers de conventions et les templates de PR, et n'affiche qu'une ligne
"cle: valeur" par information. N'affiche jamais l'URL d'un depot distant ni le
contenu d'un fichier : un fichier sensible modifie est signale par son nom.

Usage :
    python etat_depot.py [--github] [--git <executable>] [--gh <executable>]

--github ajoute les verifications propres a la livraison complete : gh
present et authentifie, depot GitHub, branche par defaut, PR de la branche.

Codes de sortie : 0 etat releve ; 1 erreur d'usage ; 2 anomalie
d'environnement (git ou gh absent, gh non authentifie, hors d'un depot git).

Python >= 3.10, bibliotheque standard seule.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Delai maximal d'une commande git ou gh : gh interroge l'API GitHub.
CMD_TIMEOUT_S = 60

# Fichiers d'instructions et de contribution lus a la phase 2, dans l'ordre.
CONVENTION_FILES = (
    "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md",
    "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
)
COMMITLINT_GLOBS = ("commitlint.config.*", ".commitlintrc*")
# Templates de PR, dans l'ordre de recherche de la phase 5.
PR_TEMPLATE_FILES = (
    ".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md",
    "PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md",
)
PR_TEMPLATE_DIR = ".github/PULL_REQUEST_TEMPLATE"

# Noms de fichiers susceptibles de contenir une donnee sensible ; compares au
# nom seul, sans le dossier. Un fichier d'exemple n'est pas signale.
SENSITIVE_GLOBS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*",
    "id_ecdsa*", "id_ed25519*", "*credentials*", ".netrc", ".pypirc", ".npmrc",
)
EXAMPLE_SUFFIXES = (".example", ".sample", ".dist", ".template")

EXIT_OK, EXIT_USAGE, EXIT_ENV = 0, 1, 2


class EnvError(Exception):
    """Anomalie d'environnement : code de sortie 2."""


class Runner:
    """Lance un executable (git ou gh) et rend sa sortie standard."""

    def __init__(self, exe: str, name: str):
        self.name = name
        self.cmd = self._resolve(exe, name)

    @staticmethod
    def _resolve(exe: str, name: str) -> list[str]:
        # Un executable .py est lance par l'interpreteur courant : c'est ainsi
        # que les tests substituent un faux git ou un faux gh.
        if exe.endswith(".py"):
            if not Path(exe).is_file():
                raise EnvError(f"{name} introuvable : {exe}")
            return [sys.executable, exe]
        found = shutil.which(exe)
        if not found:
            raise EnvError(f"{name} introuvable dans le PATH ({exe})")
        return [found]

    def run(self, *args: str) -> tuple[int, str, str]:
        try:
            res = subprocess.run([*self.cmd, *args], capture_output=True,
                                 timeout=CMD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise EnvError(f"{self.name} {' '.join(args)} : sans reponse apres {CMD_TIMEOUT_S:d} s")
        out = res.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        err = res.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")
        return res.returncode, out, err

    def value(self, *args: str) -> str | None:
        """Sortie nettoyee, ou None si la commande echoue."""
        code, out, _ = self.run(*args)
        return out.strip() if code == 0 else None


def is_sensitive(path: str) -> bool:
    name = PurePosixPath(path).name
    if name.lower().endswith(EXAMPLE_SUFFIXES):
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in SENSITIVE_GLOBS)


def parse_porcelain(text: str) -> tuple[int, int, int, list[str]]:
    """Compte indexes, non indexes et non suivis ; rend les chemins touches."""
    staged = unstaged = untracked = 0
    paths: list[str] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        x, y, path = line[0], line[1], line[3:]
        if " -> " in path:  # renommage : seul le nouveau chemin compte
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if x == "?":
            untracked += 1
        else:
            staged += x != " "
            unstaged += y != " "
        paths.append(path)
    return staged, unstaged, untracked, paths


def find_files(root: Path, names: tuple[str, ...]) -> list[str]:
    return [n for n in names if (root / n).is_file()]


def find_globs(root: Path, patterns: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        found += sorted(p.name for p in root.glob(pattern) if p.is_file())
    return found


def pr_templates(root: Path) -> list[str]:
    found = find_files(root, PR_TEMPLATE_FILES)
    folder = root / PR_TEMPLATE_DIR
    if folder.is_dir():
        found += sorted(PR_TEMPLATE_DIR + "/" + p.name for p in folder.glob("*.md"))
    return found


def commit_msg_hook(git: Runner, root: Path, git_dir: Path) -> tuple[str, str]:
    hooks_path = git.value("config", "core.hooksPath")
    folder = (root / hooks_path) if hooks_path else (git_dir / "hooks")
    label = hooks_path or "defaut"
    return label, "present" if (folder / "commit-msg").is_file() else "absent"


def default_branch_local(git: Runner, remotes: list[str]) -> tuple[str | None, str]:
    """Branche par defaut sans gh : origin/HEAD, puis main ou master locales."""
    if "origin" in remotes:
        ref = git.value("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        if ref and ref.startswith("origin/"):
            return ref[len("origin/"):], "origin/HEAD"
    for name in ("main", "master"):
        if git.value("rev-parse", "--verify", "--quiet", f"refs/heads/{name}") is not None:
            return name, "branche locale, a confirmer par les regles du projet"
    return None, "indeterminee"


def count_ahead(git: Runner, ref: str) -> str:
    value = git.value("rev-list", "--count", f"{ref}..HEAD")
    return value if value is not None else "indetermine"


def github_state(gh: Runner) -> tuple[list[tuple[str, str]], str | None]:
    """Lignes propres a GitHub et branche par defaut declaree par le depot."""
    code, _, _ = gh.run("auth", "status")
    if code != 0:
        # La sortie de gh auth status n'est jamais relayee.
        raise EnvError("gh non authentifie : l'utilisateur lance lui-meme gh auth login")
    lines: list[tuple[str, str]] = []
    code, out, err = gh.run("repo", "view", "--json", "nameWithOwner,defaultBranchRef")
    if code != 0:
        raise EnvError(f"gh repo view : code {code} ({first_line(err)})")
    repo = json.loads(out)
    base = (repo.get("defaultBranchRef") or {}).get("name") or None
    lines.append(("depot_github", repo.get("nameWithOwner", "?")))
    code, out, err = gh.run("pr", "view", "--json", "number,url,state,baseRefName")
    if code == 0:
        pr = json.loads(out)
        lines.append(("pr", f"#{pr['number']} {pr['state']} base={pr['baseRefName']} {pr['url']}"))
    elif "no pull requests found" in err.lower():
        lines.append(("pr", "aucune"))
    else:
        lines.append(("pr", f"indeterminee ({first_line(err)})"))
    return lines, base


def first_line(text: str) -> str:
    return (text.strip().splitlines() or [""])[0][:160]


def collect(git: Runner, gh: Runner | None) -> list[tuple[str, str]]:
    git_dir_raw = git.value("rev-parse", "--absolute-git-dir")
    root_raw = git.value("rev-parse", "--show-toplevel")
    if not git_dir_raw or not root_raw:
        raise EnvError("le dossier courant n'est pas dans un depot git")
    git_dir, root = Path(git_dir_raw), Path(root_raw)
    lines: list[tuple[str, str]] = [("racine", root.as_posix()), ("git_dir", git_dir.as_posix())]

    branch = git.value("branch", "--show-current") or "(HEAD detachee)"
    lines.append(("branche", branch))
    remotes = (git.value("remote") or "").split()
    lines.append(("distants", ", ".join(remotes) or "aucun"))

    gh_lines: list[tuple[str, str]] = []
    base, source = None, "indeterminee"
    if gh is not None:
        gh_lines, base = github_state(gh)
        source = "depot GitHub"
    if base is None:
        base, source = default_branch_local(git, remotes)
    lines.append(("base", f"{base} ({source})" if base else source))

    has_commit = git.value("rev-parse", "--verify", "--quiet", "HEAD") is not None
    upstream = git.value("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    lines.append(("suivi", upstream or "aucun"))
    # Reference de la base : la branche distante quand elle existe, plus a jour
    # que la branche locale du meme nom.
    remote_base = None
    if base and "origin" in remotes and git.value(
            "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{base}") is not None:
        remote_base = f"origin/{base}"
    if not has_commit:
        lines.append(("a_pousser", "aucun commit"))
    elif upstream:
        lines.append(("a_pousser", f"{count_ahead(git, upstream)} (sur {upstream})"))
    elif remote_base:
        lines.append(("a_pousser", f"{count_ahead(git, remote_base)} (sur {remote_base})"))
    else:
        lines.append(("a_pousser", "sans objet (aucune branche distante de reference)"))
    base_ref = remote_base or (base if base and git.value(
        "rev-parse", "--verify", "--quiet", f"refs/heads/{base}") is not None else None)
    if has_commit and base_ref and base != branch:
        lines.append(("avance_sur_base", f"{count_ahead(git, base_ref)} (sur {base_ref})"))

    # Sortie brute : la premiere colonne du format porcelain peut etre un espace.
    code, status, _ = git.run("status", "--porcelain=v1", "--untracked-files=all")
    if code != 0:
        raise EnvError("git status en echec")
    staged, unstaged, untracked, paths = parse_porcelain(status)
    lines.append(("modifications", f"{staged} indexee(s), {unstaged} non indexee(s), {untracked} non suivie(s)"))
    sensitive = sorted({p for p in paths if is_sensitive(p)})
    lines.append(("sensibles", ", ".join(sensitive) or "aucun"))
    if sensitive:
        lines.append(("exclusions_diff", " ".join(f"':(exclude){p}'" for p in sensitive)))

    lines.append(("conventions", ", ".join(find_files(root, CONVENTION_FILES)) or "aucune"))
    hooks_label, hook = commit_msg_hook(git, root, git_dir)
    lines.append(("hooks_path", hooks_label))
    lines.append(("hook_commit_msg", hook))
    lines.append(("commitlint", ", ".join(find_globs(root, COMMITLINT_GLOBS)) or "aucun"))
    lines.append(("templates_pr", ", ".join(pr_templates(root)) or "aucun"))
    return lines + gh_lines


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # erreur d'usage : code 1, pas 2
        self.print_usage(sys.stderr)
        sys.stderr.write(f"etat_depot.py : {message}\n")
        sys.exit(EXIT_USAGE)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    p = Parser(description="Etat du depot git en lecture seule (pull-request)")
    p.add_argument("--github", action="store_true",
                   help="ajouter gh : authentification, depot, PR de la branche")
    p.add_argument("--git", default="git", help="executable git (defaut : git du PATH)")
    p.add_argument("--gh", default="gh", help="executable gh (defaut : gh du PATH)")
    args = p.parse_args(argv)
    try:
        git = Runner(args.git, "git")
        gh = Runner(args.gh, "gh") if args.github else None
        lines = collect(git, gh)
    except EnvError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return EXIT_ENV
    width = max(len(key) for key, _ in lines)
    for key, value in lines:
        print(f"{key.ljust(width)} : {value}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
