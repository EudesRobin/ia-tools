#!/usr/bin/env python3
"""Etat du depot git pour la skill pull-request, en lecture seule.

Lance la sequence fixe des commandes git (et gh avec --github), repere les
fichiers de conventions et les templates de PR, et n'affiche qu'une ligne
"cle: valeur" par information. N'affiche jamais l'URL d'un depot distant ni le
contenu d'un fichier : un fichier sensible modifie est signale par son nom.

Usage :
    python etat_depot.py [--github | --post-merge] [--git <executable>] [--gh <executable>]

--github ajoute les verifications propres a la livraison complete : gh
present et authentifie, depot GitHub, branche par defaut, PR de la branche.

--post-merge releve, apres le merge d'une PR, l'etat du worktree principal,
les branches locales dont une PR est mergee, la concordance de leur head avec
celui de la PR, et l'etat de leur worktree. Une branche n'est supprimable que
si son head est identique a celui de la PR mergee : le critere vaut aussi pour
un merge par squash ou par rebase.

Codes de sortie : 0 etat releve ; 1 erreur d'usage ; 2 anomalie
d'environnement (git ou gh absent, gh non authentifie, sortie de gh illisible,
liste des PR inaccessible, branche par defaut indeterminee, hors d'un depot
git).

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

# PR mergees examinees en post-merge, des plus recentes aux plus anciennes :
# une seule requete a l'API GitHub couvre l'historique recent, celui des
# branches locales restees en place. Une branche dont la PR est plus ancienne
# est classee non mergee.
MERGED_PR_LIMIT = 100

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


def load_json(out: str, label: str):
    """Sortie JSON de gh ; illisible -> anomalie d'environnement."""
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise EnvError(f"{label} : sortie JSON illisible")


def github_repo(gh: Runner) -> tuple[str, str | None]:
    """Authentification verifiee, puis nom du depot et branche par defaut."""
    code, _, _ = gh.run("auth", "status")
    if code != 0:
        # La sortie de gh auth status n'est jamais relayee.
        raise EnvError("gh non authentifie : l'utilisateur lance lui-meme gh auth login")
    code, out, err = gh.run("repo", "view", "--json", "nameWithOwner,defaultBranchRef")
    if code != 0:
        raise EnvError(f"gh repo view : code {code} ({first_line(err)})")
    repo = load_json(out, "gh repo view")
    base = (repo.get("defaultBranchRef") or {}).get("name") or None
    return repo.get("nameWithOwner", "?"), base


def github_state(gh: Runner) -> tuple[list[tuple[str, str]], str | None]:
    """Lignes propres a GitHub et branche par defaut declaree par le depot."""
    name, base = github_repo(gh)
    lines: list[tuple[str, str]] = [("depot_github", name)]
    code, out, err = gh.run("pr", "view", "--json", "number,url,state,baseRefName")
    if code == 0:
        pr = load_json(out, "gh pr view")
        lines.append(("pr", f"#{pr['number']} {pr['state']} base={pr['baseRefName']} {pr['url']}"))
    elif "no pull requests found" in err.lower():
        lines.append(("pr", "aucune"))
    else:
        lines.append(("pr", f"indeterminee ({first_line(err)})"))
    return lines, base


def parse_worktrees(text: str) -> list[dict]:
    """Worktrees de git worktree list --porcelain, le principal en premier :
    chemin, branche (None si HEAD detachee), verrouille, prunable. Le bloc
    d'un depot nu, sans arbre de travail, est ignore."""
    found: list[dict] = []
    for block in text.strip().split("\n\n"):
        tree = {"path": None, "branch": None, "locked": False, "prunable": False, "bare": False}
        for line in block.splitlines():
            word = line.split(" ", 1)[0]
            if word == "worktree":
                tree["path"] = Path(line[len("worktree "):])
            elif line.startswith("branch refs/heads/"):
                tree["branch"] = line[len("branch refs/heads/"):]
            elif word in ("bare", "locked", "prunable"):
                tree[word] = True
        if tree["path"] is not None and not tree["bare"]:
            found.append(tree)
    return found


def merged_prs(gh: Runner) -> dict[str, list[tuple[int, str]]]:
    """PR mergees par branche de head : [(numero, sha du head)], les plus
    recentes en premier."""
    code, out, err = gh.run("pr", "list", "--state", "merged", "--limit", str(MERGED_PR_LIMIT),
                            "--json", "number,headRefName,headRefOid")
    if code != 0:
        raise EnvError(f"gh pr list : code {code} ({first_line(err)})")
    found: dict[str, list[tuple[int, str]]] = {}
    for pr in load_json(out, "gh pr list"):
        found.setdefault(pr["headRefName"], []).append((pr["number"], pr["headRefOid"]))
    return found


def status_counts(git: Runner, path: Path, ignored: bool = False) -> tuple[int, int, int, int]:
    """Indexes, non indexes, non suivis et ignores d'un arbre de travail."""
    args = ["-C", path.as_posix(), "status", "--porcelain=v1", "--untracked-files=all"]
    if ignored:
        args.append("--ignored")
    code, out, _ = git.run(*args)
    if code != 0:
        raise EnvError(f"git status en echec dans {path.as_posix()}")
    lines = out.splitlines()
    ignored_count = sum(1 for line in lines if line.startswith("!!"))
    kept = "\n".join(line for line in lines if not line.startswith("!!"))
    staged, unstaged, untracked, _ = parse_porcelain(kept)
    return staged, unstaged, untracked, ignored_count


def worktree_state(git: Runner, tree: dict) -> str:
    """Etat d'un worktree lie avant son retrait."""
    if tree["prunable"] or not tree["path"].is_dir():
        return "absent"
    if tree["locked"]:
        return "verrouille"
    staged, unstaged, untracked, ignored = status_counts(git, tree["path"], ignored=True)
    parts = []
    if staged or unstaged or untracked:
        parts.append(f"modifie:{staged + unstaged + untracked}")
    if ignored:
        parts.append(f"ignores:{ignored}")
    return ",".join(parts) or "propre"


def head_comparison(git: Runner, branch: str, sha: str, prs: list[tuple[int, str]]) -> tuple[int, str]:
    """Numero de PR et classement du head local au regard de la PR mergee."""
    match = next((num for num, oid in prs if oid == sha), None)
    if match is not None:
        # Head identique a celui d'une PR mergee : aucun commit local perdu.
        return match, "head=identique"
    number, oid = prs[0]
    short = oid[:7]
    if git.value("cat-file", "-e", f"{oid}^{{commit}}") is None:
        return number, f"head=divergente pr_head={short} commits_locaux=indetermine"
    if git.run("merge-base", "--is-ancestor", sha, oid)[0] == 0:
        return number, f"head=en_retard pr_head={short}"
    ahead = git.value("rev-list", "--count", f"{oid}..refs/heads/{branch}") or "indetermine"
    return number, f"head=divergente pr_head={short} commits_locaux={ahead}"


def post_merge_state(git: Runner, gh: Runner) -> list[tuple[str, str]]:
    """Etat apres le merge d'une PR : branches locales mergees et worktrees.
    Les lignes branche, modifications et dernier_commit portent sur le worktree
    principal, ou s'execute le retour sur la base."""
    root_raw = git.value("rev-parse", "--show-toplevel")
    if not root_raw:
        raise EnvError("le dossier courant n'est pas dans un depot git")
    root = Path(root_raw)
    name, base = github_repo(gh)
    if base is None:
        raise EnvError("branche par defaut du depot GitHub indeterminee")

    code, out, _ = git.run("worktree", "list", "--porcelain")
    if code != 0:
        raise EnvError("git worktree list en echec")
    worktrees = parse_worktrees(out)
    main = worktrees[0] if worktrees else {"path": root, "branch": None}
    linked = {t["branch"]: t for t in worktrees[1:] if t["branch"]}

    lines: list[tuple[str, str]] = [("racine", root.as_posix())]
    lines.append(("racine_principale", main["path"].as_posix()))
    lines.append(("worktree_courant", "principal" if root == main["path"] else "lie"))
    lines.append(("depot_github", name))
    lines.append(("base", base))
    lines.append(("branche", main["branch"] or "(HEAD detachee)"))
    staged, unstaged, untracked, _ = status_counts(git, main["path"])
    lines.append(("modifications", f"{staged} indexee(s), {unstaged} non indexee(s), {untracked} non suivie(s)"))
    last = git.value("-C", main["path"].as_posix(), "log", "-1", "--format=%h %s")
    lines.append(("dernier_commit", last or "aucun"))
    if base in linked:
        lines.append(("base_extraite", linked[base]["path"].as_posix()))

    code, out, _ = git.run("for-each-ref", "refs/heads", "--format=%(refname:lstrip=2) %(objectname)")
    if code != 0:
        raise EnvError("git for-each-ref en echec")
    merged = merged_prs(gh)
    unmerged: list[str] = []
    for line in out.splitlines():
        branch, _, sha = line.strip().partition(" ")
        if not branch or branch == base:
            continue
        prs = merged.get(branch)
        if not prs:
            unmerged.append(branch)
            continue
        number, head = head_comparison(git, branch, sha, prs)
        tree = linked.get(branch)
        where = (f"worktree={tree['path'].as_posix()} etat={worktree_state(git, tree)}"
                 if tree else "worktree=aucun")
        lines.append(("mergee", f"{branch} #{number} {head} {where}"))
    lines.append(("non_mergees", ", ".join(unmerged) or "aucune"))
    return lines


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
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--github", action="store_true",
                      help="ajouter gh : authentification, depot, PR de la branche")
    mode.add_argument("--post-merge", action="store_true",
                      help="apres le merge : branches locales mergees et worktrees")
    p.add_argument("--git", default="git", help="executable git (defaut : git du PATH)")
    p.add_argument("--gh", default="gh", help="executable gh (defaut : gh du PATH)")
    args = p.parse_args(argv)
    try:
        git = Runner(args.git, "git")
        gh = Runner(args.gh, "gh") if args.github or args.post_merge else None
        lines = post_merge_state(git, gh) if args.post_merge else collect(git, gh)
    except EnvError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return EXIT_ENV
    width = max(len(key) for key, _ in lines)
    for key, value in lines:
        print(f"{key.ljust(width)} : {value}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
