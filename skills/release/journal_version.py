#!/usr/bin/env python3
"""Journal des modifications et version a publier, pour la skill release.

Lit le journal au format Keep a Changelog du depot courant, les tags git
locaux et distants, et GitHub par gh, puis, selon le mode :
  (sans option)        releve l'etat et l'etape de la publication : nouvelle,
                       attente_merge, tag, release ou rien ;
  --close X.Y.Z        clot la section non publiee sous la version X.Y.Z, ouvre
                       une section non publiee vide, met a jour les liens de
                       comparaison et verifie la section close ;
  --notes X.Y.Z        affiche le corps de la section X.Y.Z, ou l'ecrit en
                       UTF-8 dans le fichier --output ;
  --check X.Y.Z        verifie, avant le tag, la branche par defaut, la
                       presence de la version, l'absence du tag et
                       l'integration continue du commit ;
  --release TAG        releve le workflow de release du commit tague et la
                       Release GitHub.

Sans aucun depot distant, la reference est la branche par defaut locale (main,
a defaut master) et les tags locaux : --check ne compare pas HEAD a origin et
ne lit pas l'integration continue, et --release verifie le tag local (annote,
present sur la branche par defaut, message egal aux notes de la version,
precedees ou non du tag en titre). Des depots distants sans origin sont
refuses (code 1). Dans les deux cas, --check bloque sur une modification non
committee d'un fichier suivi : le journal lu doit etre celui de HEAD.

Usage :
    python journal_version.py [--close X.Y.Z [--date AAAA-MM-JJ]
                              | --notes X.Y.Z [--title <titre>] [--output <fichier>]
                              | --check X.Y.Z | --release TAG]
                              [--file <journal>] [--base <branche>]
                              [--tag-prefix v|none]

Codes de sortie : 0 etat releve ou operation faite ; 1 erreur d'usage,
operation refusee ou verification en echec ; 2 anomalie d'environnement (git
absent, hors d'un depot git, journal introuvable ou illisible, ecriture
impossible).

Les variables JOURNAL_VERSION_FAKE_GIT et JOURNAL_VERSION_FAKE_GH designent, pour
les tests seulement, un faux git et un faux gh ecrits en Python.

Python >= 3.10, bibliotheque standard seule.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# Delai maximal d'une commande : git ls-remote et gh interrogent le reseau.
CMD_TIMEOUT_S = 60
FAKE_ENV = {"git": "JOURNAL_VERSION_FAKE_GIT", "gh": "JOURNAL_VERSION_FAKE_GH"}

# Emplacements du journal, dans l'ordre de recherche.
CHANGELOG_FILES = ("CHANGELOG.md", "docs/CHANGELOG.md", "CHANGES.md", "HISTORY.md")

# Rubrique -> niveau d'incrementation. Les titres sont compares sans emoji,
# sans accents et sans casse ; une rubrique absente de la table est signalee.
MAJOR, MINOR, PATCH = "majeur", "mineur", "correctif"
HEADING_LEVELS = {
    MAJOR: ("removed", "breaking", "breaking changes", "action requise",
            "suppressions", "supprime", "changements incompatibles"),
    MINOR: ("added", "changed", "deprecated", "features", "nouveautes", "ajoute",
            "modifications", "modifie", "obsolescences", "obsolete"),
    PATCH: ("fixed", "security", "documentation", "docs", "maintenance",
            "corrections", "corrige", "securite", "performance", "chore"),
}
LEVEL_RANK = {PATCH: 0, MINOR: 1, MAJOR: 2}
# Noms d'une section non publiee, normalises.
UNRELEASED_NAMES = {"unreleased", "non publie", "upcoming", "a venir", "next", "prochaine version"}

TITLE_VERSION_RE = re.compile(r"^\[?(?P<prefix>v?)(?P<num>\d+\.\d+\.\d+)\b")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TAG_RE = re.compile(r"^(?P<prefix>v?)(?P<num>\d+\.\d+\.\d+)$")
LINK_RE = re.compile(r"^\[(?P<name>[^\]]+)\]:\s*(?P<url>\S+)\s*$")
COMPARE_RE = re.compile(r"^(?P<head>\S+/compare/)(?P<prev>\S+?)\.\.\.HEAD$")
ENTRY_RE = re.compile(r"^[-*] +\S")

# Workflow de release : declencheur on.push.tags, et creation de la Release.
ON_KEY_RE = re.compile(r"""^["']?on["']?\s*:""")
TAGS_KEY_RE = re.compile(r"^\s+tags\s*:|[{,]\s*tags\s*:")
RELEASE_CREATORS = ("gh release create", "softprops/action-gh-release", "ncipollo/release-action",
                    "goreleaser", "actions/create-release", "release-please")

# CI : conclusions tenues pour un succes ou un echec (gh run list).
CI_SUCCESS = {"success", "skipped", "neutral"}
CI_FAILURE = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}

# Fichiers de version du projet : (chemin, motif de la ligne de version).
VERSION_FILES = (
    ("pyproject.toml", re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)),
    ("Cargo.toml", re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)),
    ("setup.cfg", re.compile(r"^version\s*=\s*(\S+)", re.MULTILINE)),
)

EXIT_OK, EXIT_FAIL, EXIT_ENV = 0, 1, 2


class EnvError(Exception):
    """Anomalie d'environnement : code de sortie 2."""


class Refused(Exception):
    """Operation refusee : code de sortie 1."""


class Runner:
    """Lance git ou gh ; un faux executable Python n'est admis que par la
    variable d'environnement de test."""

    def __init__(self, name: str, required: bool = True):
        self.name = name
        fake = os.environ.get(FAKE_ENV[name])
        found = shutil.which(name)
        if fake:
            self.cmd = [sys.executable, fake]
        elif found:
            self.cmd = [found]
        elif required:
            raise EnvError(f"{name} introuvable dans le PATH")
        else:
            self.cmd = None

    def run(self, *args: str) -> tuple[int, str, str]:
        if self.cmd is None:
            return 127, "", f"{self.name} absent"
        try:
            res = subprocess.run([*self.cmd, *args], capture_output=True, timeout=CMD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return 124, "", f"{self.name} {' '.join(args)} : sans reponse apres {CMD_TIMEOUT_S:d} s"
        out = res.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        err = res.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")
        return res.returncode, out, err

    def value(self, *args: str) -> str | None:
        code, out, _ = self.run(*args)
        return out.strip() if code == 0 else None


def normalize(title: str) -> str:
    """Titre sans emoji, sans accents, en minuscules."""
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z ]", " ", text)
    return " ".join(text.lower().split())


def heading_level(title: str) -> str | None:
    key = normalize(title)
    return next((lvl for lvl, names in HEADING_LEVELS.items() if key in names), None)


def version_key(num: str) -> tuple[int, int, int]:
    return tuple(int(x) for x in num.split("."))


def fmt(v: tuple[int, int, int]) -> str:
    return ".".join(str(x) for x in v)


class Journal:
    """Journal Keep a Changelog : sections '## ', rubriques '### ', entrees,
    definitions de liens."""

    def __init__(self, text: str):
        self.text = text.lstrip("﻿").replace("\r\n", "\n")
        self.lines = self.text.split("\n")
        self.sections: list[dict] = []
        self.links: list[tuple[int, str, str]] = []
        for i, line in enumerate(self.lines):
            m = LINK_RE.match(line)
            if m:
                self.links.append((i, m["name"], m["url"]))
            elif line.startswith("## "):
                self.sections.append(self._section(i, line[3:].strip()))
            elif self.sections:
                s = self.sections[-1]
                s["body"].append(line)
                if line.startswith("### "):
                    s["headings"].append([line[4:].strip(), 0])
                elif ENTRY_RE.match(line):
                    if s["headings"]:
                        s["headings"][-1][1] += 1
                    else:
                        s["loose"] += 1

    @staticmethod
    def _section(index: int, title: str) -> dict:
        bracket = title.startswith("[")
        name = title[1:title.index("]")] if bracket and "]" in title else title.split()[0]
        m = TITLE_VERSION_RE.match(title)
        date = DATE_RE.search(title)
        return {"index": index, "title": title, "name": name, "bracket": bracket,
                "prefix": m["prefix"] if m else "", "num": m["num"] if m else None,
                "date": date.group(0) if date else None, "headings": [], "loose": 0, "body": []}

    def unreleased(self) -> dict | None:
        """La section non publiee : la premiere, nommee comme telle, ou sans
        version ni date."""
        if not self.sections:
            return None
        s = self.sections[0]
        if s["num"] is None and (normalize(s["name"]) in UNRELEASED_NAMES or s["date"] is None):
            return s
        return None

    def versions(self) -> list[dict]:
        return [s for s in self.sections if s["num"]]

    def find(self, num: str) -> dict | None:
        return next((s for s in self.versions() if s["num"] == num), None)

    @staticmethod
    def entries(section: dict | None) -> int:
        if section is None:
            return 0
        return section["loose"] + sum(count for _, count in section["headings"])

    def link(self, name: str) -> tuple[int, str, str] | None:
        """Definition de lien d'un libelle ; la casse ne compte pas."""
        return next((l for l in self.links if l[1].casefold() == name.casefold()), None)

    def notes(self, num: str) -> str:
        s = self.find(num)
        body = "\n".join(s["body"]).strip() if s else ""
        if not body:
            raise Refused(f"section '{num}' absente ou vide")
        return body


class Repo:
    """Depot git courant : racine, journal, tags et branche par defaut."""

    def __init__(self, git: Runner, gh: Runner, explicit_file: str | None, base: str | None,
                 tag_prefix: str | None = None):
        self.git, self.gh = git, gh
        self.tag_prefix = tag_prefix
        root = git.value("rev-parse", "--show-toplevel")
        if not root:
            raise EnvError("le dossier courant n'est pas dans un depot git")
        self.root = Path(root)
        self.path = self._find(explicit_file)
        try:
            self.rel = self.path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            self.rel = None  # journal hors du depot : aucune lecture sur origin
        self.journal = Journal(self.read(self.path))
        remotes = (git.value("remote") or "").split()
        if remotes and "origin" not in remotes:
            raise Refused(f"depots distants sans origin ({', '.join(remotes)}) : cas non couvert")
        self.local = not remotes
        self.base = base or self._base()
        self._remote_tags: set[str] | None | bool = False

    def _find(self, explicit: str | None) -> Path:
        if explicit:
            path = Path(explicit)
            path = path if path.is_absolute() else self.root / path
            if not path.is_file():
                raise EnvError(f"journal introuvable : {explicit}")
            return path
        for name in CHANGELOG_FILES:
            if (self.root / name).is_file():
                return self.root / name
        raise EnvError(f"aucun journal parmi {', '.join(CHANGELOG_FILES)}")

    @staticmethod
    def read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise EnvError(f"{path.as_posix()} : illisible en UTF-8")
        except OSError as exc:
            raise EnvError(f"{path.as_posix()} : lecture impossible ({exc.strerror})")

    def _base(self) -> str | None:
        if self.local:
            for name in ("main", "master"):
                if self.git.value("rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
                    return name
            return None
        ref = self.git.value("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        if ref and ref.startswith("origin/"):
            return ref[len("origin/"):]
        for name in ("main", "master"):
            if self.git.value("rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{name}"):
                return name
        return None

    def local_tags(self) -> list[str]:
        out = self.git.value("tag", "--list", "--sort=-v:refname") or ""
        return [t.strip() for t in out.splitlines() if TAG_RE.match(t.strip())]

    def remote_tags(self) -> set[str] | None:
        """Tags du depot distant origin, None si illisibles."""
        if self.local:
            return None
        if self._remote_tags is False:
            out = self.git.value("ls-remote", "--tags", "origin")
            if out is None:
                self._remote_tags = None
            else:
                names = {line.split("refs/tags/", 1)[1].removesuffix("^{}")
                         for line in out.splitlines() if "refs/tags/" in line}
                self._remote_tags = {n for n in names if TAG_RE.match(n)}
        return self._remote_tags

    def all_tags(self) -> list[str]:
        tags = set(self.local_tags()) | (self.remote_tags() or set())
        return sorted(tags, key=lambda t: version_key(TAG_RE.match(t)["num"]), reverse=True)

    def prefix(self) -> str | None:
        """Prefixe des tags : celui des tags existants, a defaut celui des liens
        de comparaison ; None s'il reste indetermine. --tag-prefix l'emporte."""
        if self.tag_prefix is not None:
            return self.tag_prefix
        tags = self.all_tags()
        if tags:
            return TAG_RE.match(tags[0])["prefix"]
        for _, _, url in self.journal.links:
            m = re.search(r"/compare/(v?)\d+\.\d+\.\d+\.\.\.", url) or re.search(r"/tag/(v?)\d", url)
            if m:
                return m.group(1)
        return None

    def base_ref(self) -> str | None:
        """Reference partagee : origin/<base>, ou <base> dans un depot local."""
        if not self.base:
            return None
        return self.base if self.local else f"origin/{self.base}"

    def base_journal(self) -> Journal | None:
        """Journal de la reference partagee (origin/<base> apres un git fetch)."""
        if not self.base_ref() or not self.rel:
            return None
        text = self.git.value("show", f"{self.base_ref()}:{self.rel}")
        return Journal(text) if text is not None else None

    def release_url(self, tag: str) -> str | None | bool:
        """URL de la Release, None si absente, False si gh ne repond pas."""
        code, out, err = self.gh.run("release", "view", tag, "--json", "url,isDraft")
        if code == 0:
            data = json.loads(out or "{}")
            return data.get("url", "?") + (" (brouillon)" if data.get("isDraft") else "")
        return None if "not found" in err.lower() else False


def bump(base: tuple[int, int, int], level: str) -> tuple[tuple[int, int, int], str]:
    major, minor, patch = base
    if level == MAJOR and major == 0:
        return (0, minor + 1, 0), "version 0.y.z : un changement incompatible incremente MINEUR"
    if level == MAJOR:
        return (major + 1, 0, 0), ""
    if level == MINOR:
        return (major, minor + 1, 0), ""
    return (major, minor, patch + 1), ""


def release_workflows(root: Path) -> list[tuple[str, bool]]:
    """Workflows declenches par un tag (on.push.tags) : (fichier, cree la Release)."""
    folder = root / ".github" / "workflows"
    found = []
    for path in sorted(folder.glob("*.y*ml")) if folder.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        block, inside = [], False
        for line in text.splitlines():
            if ON_KEY_RE.match(line):
                inside = True
                block.append(line)
            elif inside and line and not line[0].isspace() and not line.startswith("#"):
                break
            elif inside:
                block.append(line)
        if any(TAGS_KEY_RE.search(line) for line in block):
            found.append((path.name, any(c in text for c in RELEASE_CREATORS)))
    return found


def version_files(root: Path) -> list[str]:
    found = []
    for name, regex in VERSION_FILES:
        path = root / name
        if path.is_file():
            m = regex.search(path.read_text(encoding="utf-8", errors="replace"))
            if m:
                found.append(f"{name} ({m.group(1)})")
    package = root / "package.json"
    if package.is_file():
        try:
            version = json.loads(package.read_text(encoding="utf-8-sig")).get("version")
        except (ValueError, AttributeError):
            version = None
        if version:
            found.append(f"package.json ({version})")
    return found


def step(repo: Repo) -> str:
    """Etape de la publication, d'apres origin/<base>, les tags distants et la
    Release ; dans un depot local, d'apres <base> et les tags locaux."""
    journal = repo.journal
    shared = repo.base_journal()
    reference = shared or journal
    where = repo.base_ref() if shared else "journal local"
    remote = repo.remote_tags()
    prefix = repo.prefix() or ""
    # Tags distants : un tag pose localement mais non pousse n'est pas publie.
    known = remote if remote is not None else set(repo.local_tags())
    newest_tag = max((version_key(TAG_RE.match(t)["num"]) for t in known), default=None)
    last = reference.versions()[0] if reference.versions() else None
    if last:
        tag = prefix + last["num"]
        is_newer = newest_tag is None or version_key(last["num"]) > newest_tag
        if tag not in known and is_newer:
            return f"tag ({last['num']}, close sur {where})"
        if tag in known and repo.gh.cmd is not None and not repo.local:
            url = repo.release_url(tag)
            if url is None:
                return f"release ({tag}, tag pose, Release absente)"
    local_last = journal.versions()[0] if journal.versions() else None
    if local_last and (last is None or version_key(local_last["num"]) > version_key(last["num"])):
        return f"attente_merge ({local_last['num']}, close localement, absente de {where})"
    if Journal.entries(journal.unreleased()):
        return "nouvelle"
    return "rien"


def state(repo: Repo) -> list[tuple[str, str]]:
    journal = repo.journal
    lines: list[tuple[str, str]] = [("journal", repo.rel or repo.path.as_posix())]
    git_dir = repo.git.value("rev-parse", "--absolute-git-dir")
    lines.append(("git_dir", Path(git_dir).as_posix() if git_dir else "indetermine"))
    lines.append(("distant", "aucun (depot local)" if repo.local else "origin"))
    lines.append(("base", repo.base or "indeterminee"))
    pending = journal.unreleased()
    lines.append(("section_non_publiee", pending["name"] if pending else "absente"))

    level, unknown, total = None, [], Journal.entries(pending)
    if pending:
        parts = [f"{title} ({count})" for title, count in pending["headings"]]
        if pending["loose"]:
            parts.append(f"sans rubrique ({pending['loose']})")
            unknown.append("sans rubrique")
        for title, count in pending["headings"]:
            lvl = heading_level(title)
            if lvl is None:
                unknown.append(title)
            elif count and (level is None or LEVEL_RANK[lvl] > LEVEL_RANK[level]):
                level = lvl
        lines.append(("rubriques", ", ".join(parts) or "aucune"))
        lines.append(("entrees", str(total)))
        if unknown:
            lines.append(("rubriques_inconnues", ", ".join(unknown) + " (ecartees du calcul)"))

    last = journal.versions()[0] if journal.versions() else None
    lines.append(("derniere_version", f"{last['num']} ({last['date'] or 'sans date'})" if last else "aucune"))
    tags = repo.all_tags()
    lines.append(("dernier_tag", tags[0] if tags else "aucun"))
    prefix = repo.prefix()
    lines.append(("prefixe_tag", {None: "indetermine (aucun tag ni lien)", "": "aucun"}.get(prefix, prefix)))

    bases = [version_key(x) for x in ((last or {}).get("num"),
                                      TAG_RE.match(tags[0])["num"] if tags else None) if x]
    if not total:
        lines.append(("proposition", "aucune (section non publiee vide ou absente)"))
    elif not bases:
        lines.append(("proposition", "1.0.0 (premiere version ; 0.1.0 si l'API n'est pas stable)"))
    else:
        base = max(bases)
        lvl = level or PATCH
        new, note = bump(base, lvl)
        lines.append(("proposition", f"{fmt(new)} ({lvl} depuis {fmt(base)}{' ; ' + note if note else ''})"))

    link = journal.link(pending["name"]) if pending else None
    if link and COMPARE_RE.match(link[2]):
        lines.append(("liens", "comparaison"))
    elif journal.links:
        lines.append(("liens", f"absents pour {pending['name']}" if pending and not link
                      else "hors modele de comparaison"))
    else:
        lines.append(("liens", "aucun"))
    workflows = release_workflows(repo.root)
    lines.append(("workflow_release", ", ".join(
        f"{name} ({'cree la Release' if creates else 'sans creation de Release'})"
        for name, creates in workflows) or "aucun"))
    lines.append(("fichiers_version", ", ".join(version_files(repo.root)) or "aucun"))
    lines.append(("etape", step(repo)))
    return lines


def close(repo: Repo, version: str, date: str) -> list[tuple[str, str]]:
    m = TAG_RE.match(version)
    if not m or m["prefix"]:
        raise Refused(f"version '{version}' non conforme, attendu X.Y.Z sans prefixe")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise Refused(f"date '{date}' invalide, attendu AAAA-MM-JJ")
    journal = repo.journal
    pending = journal.unreleased()
    if pending is None:
        raise Refused(f"{repo.rel or repo.path} : la premiere section n'est pas une section non publiee")
    if not Journal.entries(pending):
        raise Refused(f"{repo.rel or repo.path} : section '{pending['name']}' sans entree, rien a publier")
    known = [version_key(s["num"]) for s in journal.versions()]
    known += [version_key(TAG_RE.match(t)["num"]) for t in repo.all_tags()]
    # Les tags comptent : une version deja taguee n'est jamais superieure.
    if known and version_key(version) <= max(known):
        raise Refused(f"{version} n'est pas superieure a {fmt(max(known))}, "
                      "derniere version du journal ou des tags")

    raw = repo.path.read_bytes().decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = list(journal.lines)
    last = journal.versions()[0] if journal.versions() else None
    shown = (last["prefix"] if last else "") + version
    heading = f"## [{shown}] - {date}" if pending["bracket"] else f"## {shown} - {date}"
    at = pending["index"]
    lines[at + 1:at + 1] = ["", heading]

    prefix = repo.prefix() or ""
    link = journal.link(pending["name"])
    if link is None:
        links_state = f"absents pour {pending['name']}" if journal.links else "aucun"
    elif not COMPARE_RE.match(link[2]):
        links_state = "non mis a jour (lien hors modele de comparaison)"
    else:
        i, name, url = link
        head, prev = COMPARE_RE.match(url)["head"], COMPARE_RE.match(url)["prev"]
        i += 2  # deux lignes inserees plus haut
        tag = prefix + version
        lines[i] = f"[{name}]: {head}{tag}...HEAD"
        lines.insert(i + 1, f"[{shown}]: {head}{prev}...{tag}")
        links_state = "mis a jour"

    try:
        repo.path.write_bytes(newline.join(lines).encode("utf-8"))
    except OSError as exc:
        raise EnvError(f"{repo.path.as_posix()} : ecriture impossible ({exc.strerror})")

    # Post-condition : la section close reprend la section non publiee.
    written = Journal(Repo.read(repo.path))
    closed = written.find(version)
    same = (closed is not None and closed["headings"] == pending["headings"]
            and closed["loose"] == pending["loose"] and not Journal.entries(written.unreleased()))
    if not same:
        raise Refused(f"{repo.rel or repo.path} : la section {version} ne reprend pas la section close")
    return [("cloture", f"{version} - {date}"), ("section_non_publiee", f"{pending['name']} (vide)"),
            ("liens", links_state),
            ("notes", f"{len(pending['headings'])} rubrique(s), {Journal.entries(pending)} entree(s), "
                      "identiques a la section close")]


def ci_summary(gh: Runner, sha: str) -> tuple[str, bool]:
    """Resume de l'integration continue d'un commit ; vrai si tout est au vert."""
    code, out, err = gh.run("run", "list", "--commit", sha, "--json", "name,status,conclusion")
    if code != 0:
        return f"indeterminee ({(err.strip().splitlines() or [''])[0][:120]})", False
    runs = json.loads(out or "[]")
    if not runs:
        return "aucune execution", False
    pending = sum(r.get("status") != "completed" for r in runs)
    ok = sum(r.get("status") == "completed" and r.get("conclusion") in CI_SUCCESS for r in runs)
    failed = sum(r.get("status") == "completed" and r.get("conclusion") in CI_FAILURE for r in runs)
    return f"{ok} succes, {failed} echec, {pending} en cours", failed == 0 and pending == 0


def check(repo: Repo, version: str) -> tuple[list[tuple[str, str]], bool]:
    lines: list[tuple[str, str]] = []
    blockers: list[str] = []
    branch = repo.git.value("branch", "--show-current") or "(HEAD detachee)"
    lines.append(("branche", branch))
    if repo.base is None:
        blockers.append("branche par defaut indeterminee (--base)")
    elif branch != repo.base:
        blockers.append(f"branche courante differente de {repo.base}")
    sha = repo.git.value("rev-parse", "HEAD") or ""
    lines.append(("sha", sha))
    # Le journal lu est celui de la copie de travail : il doit etre celui de HEAD.
    code, out, _ = repo.git.run("status", "--porcelain", "--untracked-files=no")
    pending = [line[3:] for line in (out if code == 0 else "").splitlines() if line.strip()]
    if pending:
        shown = ", ".join(pending[:5]) + (f", +{len(pending) - 5}" if len(pending) > 5 else "")
        blockers.append(f"modifications non committees : {shown}")
    if not repo.local:
        remote_sha = repo.git.value("rev-parse", f"refs/remotes/origin/{repo.base}") if repo.base else None
        if sha != remote_sha:
            blockers.append(f"HEAD differe de origin/{repo.base} (git pull --ff-only)")
    if repo.journal.find(version) is None:
        blockers.append(f"version {version} absente de {repo.rel}")
    after = Journal.entries(repo.journal.unreleased())
    lines.append(("non_publie", f"{after} entree(s)"))
    if after:
        blockers.append("des entrees ont ete ajoutees depuis la cloture")
    tag = (repo.prefix() or "") + version
    lines.append(("tag", tag))
    if tag in repo.local_tags() or tag in (repo.remote_tags() or set()):
        blockers.append(f"le tag {tag} existe deja")
    ci, green = ("sans objet (depot local)", True) if repo.local else ci_summary(repo.gh, sha)
    lines.append(("ci", ci))
    if not green:
        blockers.append("integration continue pas au vert")
    lines.append(("verdict", "pret" if not blockers else "bloque (" + " ; ".join(blockers) + ")"))
    return lines, not blockers


def local_tag(repo: Repo, tag: str, sha: str) -> tuple[list[tuple[str, str]], bool]:
    """Depot sans distant : tag annote, sur la branche par defaut, message egal aux notes."""
    lines: list[tuple[str, str]] = []
    annotated = repo.git.value("cat-file", "-t", tag) == "tag"
    lines.append(("annote", "oui" if annotated else "non (tag leger)"))
    on_base = bool(repo.base) and repo.git.run("merge-base", "--is-ancestor", sha, repo.base)[0] == 0
    lines.append(("sur_base", "oui" if on_base else f"non (absent de {repo.base or 'base indeterminee'})"))
    m = TAG_RE.match(tag)
    try:
        notes = repo.journal.notes(m["num"]) if m else ""
    except Refused:
        notes = ""
    message = (repo.git.value("tag", "-l", "--format=%(contents)", tag) or "").strip()
    conform = bool(notes) and message in (notes, f"{tag}\n\n{notes}")
    lines.append(("notes", "conformes" if conform else
                  "differentes du journal" if notes else f"version {tag} absente du journal"))
    ok = annotated and on_base and conform
    lines.append(("verdict", "conforme" if ok else "ecart"))
    return lines, ok


def release(repo: Repo, tag: str) -> tuple[list[tuple[str, str]], bool]:
    sha = repo.git.value("rev-list", "-n", "1", tag)
    if not sha:
        raise Refused(f"tag {tag} introuvable localement")
    lines = [("tag", tag), ("sha", sha)]
    if repo.local:
        checked, ok = local_tag(repo, tag, sha)
        return lines + checked, ok
    for name, creates in release_workflows(repo.root):
        code, out, _ = repo.gh.run("run", "list", "--workflow", name, "--commit", sha,
                                   "--json", "status,conclusion")
        runs = json.loads(out or "[]") if code == 0 else None
        if runs is None:
            status = "indetermine"
        elif not runs:
            status = "aucune execution"
        else:
            r = runs[0]
            status = r.get("conclusion") or r.get("status") if r.get("status") == "completed" else "en cours"
        lines.append(("workflow", f"{name} : {status}{'' if creates else ' (sans creation de Release)'}"))
    url = repo.release_url(tag)
    lines.append(("release", "indeterminee (gh)" if url is False else url or "absente"))
    return lines, True


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # erreur d'usage : code 1, pas 2
        self.print_usage(sys.stderr)
        sys.stderr.write(f"journal_version.py : {message}\n")
        sys.exit(EXIT_FAIL)


def main(argv: list[str] | None = None) -> int:
    p = Parser(description="Journal des modifications et version a publier (release)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--close", metavar="X.Y.Z", help="clore la section non publiee")
    mode.add_argument("--notes", metavar="X.Y.Z", help="notes d'une version")
    mode.add_argument("--check", metavar="X.Y.Z", help="verifier la branche par defaut avant le tag")
    mode.add_argument("--release", metavar="TAG", help="workflow de release et Release d'un tag")
    p.add_argument("--date", default=datetime.date.today().isoformat(),
                   help="date de la version close (defaut : aujourd'hui)")
    p.add_argument("--output", help="avec --notes : fichier ecrit en UTF-8")
    p.add_argument("--title", help="avec --notes : premiere ligne ecrite avant les notes (sujet d'un tag)")
    p.add_argument("--file", help="journal, relatif a la racine du depot (defaut : recherche)")
    p.add_argument("--base", help="branche par defaut (defaut : origin/HEAD ; depot local : main, a defaut master)")
    p.add_argument("--tag-prefix", choices=("v", "none"),
                   help="prefixe des tags quand il est indetermine (v ou none)")
    args = p.parse_args(argv)
    if (args.output or args.title) and not args.notes:
        p.error("--output et --title ne s'emploient qu'avec --notes")
    # Emojis et accents des rubriques : sortie en UTF-8 quelle que soit la console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code = EXIT_OK
    try:
        prefix = {"v": "v", "none": ""}.get(args.tag_prefix)
        repo = Repo(Runner("git"), Runner("gh", required=False), args.file, args.base, prefix)
        if args.notes:
            body = repo.journal.notes(args.notes)
            if args.title:
                body = f"{args.title}\n\n{body}"
            if not args.output:
                print(body)
                return EXIT_OK
            out = Path(args.output)
            try:
                out.write_bytes((body + "\n").encode("utf-8"))
            except OSError as exc:
                raise EnvError(f"{out.as_posix()} : ecriture impossible ({exc.strerror})")
            lines = [("notes", f"{out.as_posix()} ({len(body.splitlines())} lignes, UTF-8)")]
        elif args.close:
            lines = close(repo, args.close, args.date)
        elif args.check:
            lines, ok = check(repo, args.check)
            code = EXIT_OK if ok else EXIT_FAIL
        elif args.release:
            lines, ok = release(repo, args.release)
            code = EXIT_OK if ok else EXIT_FAIL
        else:
            lines = state(repo)
    except EnvError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return EXIT_ENV
    except Refused as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return EXIT_FAIL
    width = max(len(key) for key, _ in lines)
    for key, value in lines:
        print(f"{key.ljust(width)} : {value}")
    return code


if __name__ == "__main__":
    sys.exit(main())
