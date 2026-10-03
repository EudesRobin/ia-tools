#!/usr/bin/env python3
"""Merge intelligent du depot vers chaque agent hote (docs/SETUP.md).

Agents hotes pris en charge, dont la racine est notee {AGENT_DIR} :

  claude    ~/.claude     agent installe sous <nom>.md
  copilot   ~/.copilot    agent installe sous <nom>.agent.md

Pour chaque agent hote, classe chaque fichier distribue par ce depot face a sa
cible locale, applique les cas surs sur demande, et laisse a la session les
seuls conflits :

  absent      cible inexistante                        -> ecrire le rendu
  identique   rendu == cible                           -> rien
  obsolete    cible == rendu d'une revision anterieure  -> ecrire le rendu
  conflit     ni l'un ni l'autre : edition locale       -> arbitrage humain
  local-seul  present seulement en local, dans le dossier
              d'un outil du depot                     -> liste, jamais supprime

Un outil (une skill, un agent et ses documents) s'installe d'un bloc chez un
agent hote : si l'un de ses fichiers y est en conflit, aucun de ses fichiers n'y
est ecrit. Un outil homonyme cree par l'utilisateur n'est donc jamais complete
ni modifie. Chaque agent hote est traite separement.

Le rendu est la source apres substitution des placeholders {NOM_VARIABLE}
(docs/SETUP.md section 1). La comparaison normalise les fins de ligne ; l'ecriture
recopie les octets du rendu, ce qui preserve celles de l'arbre de travail.

Garde-fou non negociable : le settings.json d'un agent hote et ses fichiers
d'enregistrement de hooks ne sont jamais ecrits. Ce qui reste a fusionner est
affiche, pas applique. Il en va de meme pour la cle statusLine d'une status
line : l'audit lit settings.json, indique si la cle designe le script installe
et affiche le fragment a fusionner.

Une status line est propre a un agent hote, que nomme son dossier source :
statuslines/<agent hote>/<nom>/ s'installe sous {AGENT_DIR}/statuslines/<nom>/.
Seul Claude Code en a aujourd'hui (SCOPE_AGENTS) : le perimetre statusline
n'est examine pour aucun autre agent hote.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell, dont l'encodage par defaut corrompt les caracteres accentues
(voir docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/install.py [--apply] [--agent ...] [--scope ...]
                                  [--tool ...] [--diff <chemin>]
                                  [--target <dossier>] [--json]
Code de sortie : 0 si aucun conflit ne reste chez aucun agent hote, 1 sinon.
"""

import argparse
import difflib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Agents hotes (docs/SETUP.md section 1) : racine {AGENT_DIR} et suffixe du
# fichier d'un agent installe. Copilot CLI n'accepte que <nom>.agent.md.
AGENTS = {
    "claude": {"root": "~/.claude", "agent_suffix": ".md"},
    "copilot": {"root": "~/.copilot", "agent_suffix": ".agent.md"},
}
DEFAULT_AGENTS = ["claude", "copilot"]

# Perimetres et paires source -> cible (docs/SETUP.md section 1).
# Un dossier source est recopie recursivement sous le dossier cible ; {agent}
# y designe l'agent hote examine.
SCOPES = {
    "skills": [("skills", "skills")],
    "agents": [("agents", "agents")],
    "hooks": [],  # aucun hook distribue : validate-tool est local au depot
    "statusline": [("statuslines/{agent}", "statuslines")],
}
DEFAULT_SCOPES = ["skills", "agents", "hooks", "statusline"]

# Perimetres reserves a certains agents hotes ; les autres les ignorent.
# scripts/validate.py n'admet sous statuslines/ que les dossiers declares ici.
SCOPE_AGENTS = {"statusline": {"claude"}}

# Script d'une status line : statuslines/<agent hote>/<nom>/statusline.ps1,
# enregistre par la cle statusLine de settings.json (docs/SETUP.md section 6).
STATUSLINE_SCRIPT = "statusline.ps1"

# Enregistrement des hooks, jamais ecrit par ce script (docs/SETUP.md section 5).
HOOK_REGISTRATION = {
    "claude": "settings.json (cle hooks)",
    "copilot": "hooks/<nom>.json",
}

# Jamais classe ni ecrit, dans le depot comme en local.
EXCLUDED_DIRS = {".idea", "__pycache__", "plugins", ".git"}
EXCLUDED_NAMES = {"settings.json", "settings.local.json", ".gitignore"}

# Profondeur d'historique exploree pour reconnaitre une installation obsolete.
HISTORY_MAX_REVS = 60


def variables(agent: str, target_root: Path, target_given: bool) -> dict[str, str]:
    """Variables substituees a l'installation (docs/SETUP.md section 1).

    Seule difference legitime entre un fichier du depot et sa cible. Une
    variable ajoutee se declare ici, avec une valeur derivee de l'environnement
    et jamais un chemin local en dur (CONVENTIONS.md section 1.2).
    """
    agent_dir = target_root.as_posix() if target_given else AGENTS[agent]["root"]
    return {"{AGENT_DIR}": agent_dir}


def is_agent_file(rel: Path) -> bool:
    """Fichier d'agent de premier niveau : agents/<nom>.md, hors agents/docs/."""
    return len(rel.parts) == 1 and rel.suffix == ".md"


def dest_rel(agent: str, src_rel: str, rel: Path) -> Path:
    """Chemin cible, relatif au dossier cible, d'un fichier source."""
    if src_rel == "agents" and is_agent_file(rel):
        return rel.with_name(rel.name.removesuffix(".md") + AGENTS[agent]["agent_suffix"])
    return rel


def source_rel(agent: str, src_rel: str, rel: Path) -> Path | None:
    """Correspondance inverse de dest_rel. None si la cible ne peut pas venir
    d'une source (un <nom>.md local pour Copilot CLI, par exemple)."""
    if src_rel == "agents" and len(rel.parts) == 1:
        suffix = AGENTS[agent]["agent_suffix"]
        if not rel.name.endswith(suffix):
            return None
        return rel.with_name(rel.name.removesuffix(suffix) + ".md")
    return rel


def tool_of(rel: str) -> str:
    """Nom de l'outil auquel appartient un chemin : skills/<nom>/...,
    agents/<nom>.md, agents/<nom>.agent.md, agents/docs/<nom>/...,
    statuslines/<agent hote>/<nom>/... (source) ou statuslines/<nom>/... (cible)."""
    parts = rel.split("/")
    if parts[0] == "statuslines" and len(parts) > 3 and parts[1] in AGENTS:
        return parts[2]
    if parts[0] == "agents":
        if parts[1] == "docs" and len(parts) > 2:
            return parts[2]
        return parts[1].removesuffix(".md").removesuffix(".agent")
    return parts[1] if len(parts) > 1 else parts[0]


def excluded(rel: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return True
    return rel.name in EXCLUDED_NAMES


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except (IsADirectoryError, FileNotFoundError, PermissionError, OSError):
        return None


def render(raw: bytes, subs: dict[str, str]) -> bytes:
    for token, value in subs.items():
        raw = raw.replace(token.encode("utf-8"), value.encode("utf-8"))
    return raw


def normalize(raw: bytes) -> bytes:
    """Forme de comparaison : fins de ligne unifiees, BOM et blancs de fin otes.

    L'arbre de travail est en CRLF sous Windows (core.autocrlf) alors que
    'git show' rend du LF : sans cette normalisation, tout fichier serait
    signale en ecart.
    """
    raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    raw = raw.removeprefix(b"\xef\xbb\xbf")
    return raw.rstrip(b"\n") + b"\n"


def git_bytes(args: list[str]) -> bytes | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout


def previous_renders(source: str, subs: dict[str, str]) -> list[bytes]:
    """Formes normalisees prises par le rendu de ce fichier dans l'historique.

    L'historique suit les renommages (--follow) : chaque revision est lue sous
    le chemin qu'avait le fichier a cette revision. Une installation faite avant
    le deplacement d'un outil reste ainsi reconnue comme obsolete.
    """
    log = git_bytes(
        ["log", "--follow", f"-{HISTORY_MAX_REVS}", "--format=@%H", "--name-only", "--", source]
    )
    if not log:
        return []
    revisions: list[tuple[str, str]] = []
    path_at_rev = source
    for line in log.decode("utf-8", errors="replace").splitlines():
        if line.startswith("@"):
            revisions.append((line[1:], path_at_rev))
        elif line.strip() and revisions:
            path_at_rev = line.strip()
            revisions[-1] = (revisions[-1][0], path_at_rev)
    renders = []
    for rev, path_at_rev in revisions:
        blob = git_bytes(["show", f"{rev}:{path_at_rev}"])
        if blob is None:
            continue
        renders.append(normalize(render(blob, subs)))
    return renders


def scope_pairs(agent: str, scope: str) -> list[tuple[str, str]]:
    """Paires (source, cible) d'un perimetre pour cet agent hote."""
    return [(src.format(agent=agent), dst) for src, dst in SCOPES[scope]]


def pairs(agent: str, scopes: list[str], target_root: Path) -> list[tuple[str, Path, Path]]:
    """(chemin source affiche, source, cible) pour tout le perimetre demande."""
    out = []
    for scope in scopes:
        for src_rel, dst_rel in scope_pairs(agent, scope):
            src = ROOT / src_rel
            dst = target_root / dst_rel
            if src.is_file():
                out.append((src_rel, src, dst))
                continue
            if not src.is_dir():
                continue
            for path in sorted(src.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(src)
                if excluded(rel):
                    continue
                out.append(
                    (f"{src_rel}/{rel.as_posix()}", path, dst / dest_rel(agent, src_rel, rel))
                )
    return out


def local_only(agent: str, scopes: list[str], target_root: Path) -> list[str]:
    """Fichiers presents seulement en local, dans le dossier d'un outil du depot.
    Listes, jamais supprimes.

    Les outils etrangers au depot (outils de l'utilisateur, skills synchronisees
    par l'agent hote) ne sont pas examines : ils ne relevent pas de ce merge.
    """
    tools = {tool_of(rel) for rel, _, _ in pairs(agent, scopes, target_root)}
    out = []
    for scope in scopes:
        for src_rel, dst_rel in scope_pairs(agent, scope):
            src, dst = ROOT / src_rel, target_root / dst_rel
            if not src.is_dir() or not dst.is_dir():
                continue
            for path in sorted(dst.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(dst)
                if excluded(rel) or tool_of(f"{dst_rel}/{rel.as_posix()}") not in tools:
                    continue
                origin = source_rel(agent, src_rel, rel)
                if origin is not None and (src / origin).is_file():
                    continue
                out.append(f"{dst_rel}/{rel.as_posix()}")
    return out


def classify(source: str, src: Path, dst: Path, subs: dict[str, str]) -> tuple[str, bytes]:
    raw = read_bytes(src)
    if raw is None:
        return "illisible", b""
    rendered = render(raw, subs)
    local = read_bytes(dst)
    if local is None:
        return "absent", rendered
    if normalize(local) == normalize(rendered):
        return "identique", rendered
    if normalize(local) in previous_renders(source, subs):
        return "obsolete", rendered
    return "conflit", rendered


def unified(agent: str, source: str, src: Path, dst: Path, subs: dict[str, str]) -> str:
    rendered = render(read_bytes(src) or b"", subs)
    local = read_bytes(dst) or b""
    return "".join(
        difflib.unified_diff(
            normalize(local).decode("utf-8", errors="replace").splitlines(True),
            normalize(rendered).decode("utf-8", errors="replace").splitlines(True),
            fromfile=f"{agent}/local/{dst.name}",
            tofile=f"depot/{source}",
        )
    )


def scopes_of(agent: str, scopes: list[str]) -> list[str]:
    """Perimetres demandes que cet agent hote prend en charge."""
    return [s for s in scopes if agent in SCOPE_AGENTS.get(s, AGENTS)]


def statusline_command(script: Path) -> str:
    """Commande attendue dans la cle statusLine. Barres obliques : Claude Code
    passe la commande a Git Bash quand il est installe. -ExecutionPolicy Bypass :
    la strategie par defaut de PowerShell 5.1 refuse les scripts."""
    interpreter = "pwsh" if shutil.which("pwsh") else "powershell"
    return (
        f'{interpreter} -NoProfile -NonInteractive -ExecutionPolicy Bypass '
        f'-File "{script.as_posix()}"'
    )


def statusline_state(agent: str, scopes: list[str], target_root: Path, tools: set[str] | None) -> dict | None:
    """Etat de la cle statusLine, en lecture seule : 'enregistree' si elle
    designe une status line du depot, 'absente', 'autre' si elle designe un
    autre script, 'illisible' si settings.json n'est pas du JSON valide."""
    if "statusline" not in scopes_of(agent, scopes):
        return None
    names = sorted(
        p.name for p in (ROOT / "statuslines" / agent).glob("*/")
        if (p / STATUSLINE_SCRIPT).is_file() and (tools is None or p.name in tools)
    )
    if not names:
        return None
    settings = target_root / "settings.json"
    key = None
    if settings.is_file():
        try:
            key = json.loads(settings.read_text(encoding="utf-8-sig")).get("statusLine")
        except (ValueError, AttributeError, OSError):
            return {"etat": "illisible", "fichier": str(settings), "fragments": {}}
    command = key.get("command", "") if isinstance(key, dict) else ""
    command = command.replace("\\", "/").lower()
    fragments = {
        name: {
            "type": "command",
            "command": statusline_command(target_root / "statuslines" / name / STATUSLINE_SCRIPT),
        }
        for name in names
    }
    for name in names:
        if f"statuslines/{name}/{STATUSLINE_SCRIPT}".lower() in command:
            return {"etat": "enregistree", "outil": name, "fichier": str(settings), "fragments": {}}
    return {
        "etat": "absente" if key is None else "autre",
        "fichier": str(settings),
        "actuelle": key,
        "fragments": fragments,
    }


def hooks_notice(agent: str, scopes: list[str], target_root: Path) -> str | None:
    """L'enregistrement des hooks n'est jamais ecrit : afficher ce qui resterait a faire."""
    if "hooks" not in scopes or SCOPES["hooks"]:
        return None
    return (
        "hooks : aucun hook distribue par ce depot (validate-tool est local au "
        f"depot).\n  {target_root / HOOK_REGISTRATION[agent]} n'est pas touche."
    )


def parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Merge intelligent du depot vers chaque agent hote (docs/SETUP.md).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="ecrire les cas surs (absent, obsolete) ; rien pour un outil en conflit",
    )
    p.add_argument(
        "--agent",
        default=",".join(DEFAULT_AGENTS),
        help=f"agents hotes separes par des virgules parmi {','.join(AGENTS)}",
    )
    p.add_argument(
        "--scope",
        default=",".join(DEFAULT_SCOPES),
        help=f"perimetres separes par des virgules parmi {','.join(SCOPES)}",
    )
    p.add_argument(
        "--tool",
        "--outil",  # ancien nom, obsolete : retire dans une prochaine version MAJEUR
        dest="tool",
        metavar="NOMS",
        help="n'examiner que ces outils, separes par des virgules (defaut : tous)",
    )
    p.add_argument(
        "--diff",
        metavar="CHEMIN",
        help="afficher le diff unifie d'un fichier (chemin source du depot), par agent hote",
    )
    p.add_argument(
        "--target",
        metavar="DOSSIER",
        help="racine cible a la place de {AGENT_DIR} ; un seul agent hote requis",
    )
    p.add_argument("--json", action="store_true", help="sortie machine")
    args = p.parse_args()
    if any(a == "--outil" or a.startswith("--outil=") for a in sys.argv[1:]):
        print("install.py : --outil est obsolete, employer --tool", file=sys.stderr)
    return args


def examine(agent: str, args: argparse.Namespace, scopes: list[str]) -> dict:
    """Classe, et ecrit si --apply, le perimetre d'un agent hote."""
    target_given = args.target is not None
    root_dir = args.target if target_given else AGENTS[agent]["root"]
    target_root = Path(root_dir).expanduser().resolve()
    subs = variables(agent, target_root, target_given)
    ignores = [s for s in scopes if s not in scopes_of(agent, scopes)]
    scopes = scopes_of(agent, scopes)
    file_pairs = pairs(agent, scopes, target_root)
    orphans = local_only(agent, scopes, target_root)
    wanted = set(parse_list(args.tool)) if args.tool else None

    if wanted is not None:
        file_pairs = [c for c in file_pairs if tool_of(c[0]) in wanted]
        orphans = [o for o in orphans if tool_of(o) in wanted]

    classes: dict[str, list[str]] = {
        "absent": [],
        "identique": [],
        "obsolete": [],
        "conflit": [],
        "illisible": [],
    }
    per_file = []
    for source, src, dst in file_pairs:
        status, rendered = classify(source, src, dst, subs)
        classes[status].append(source)
        per_file.append((source, dst, status, rendered))

    blocked = sorted({tool_of(rel) for rel in classes["conflit"]})
    written: list[str] = []
    if args.apply:
        for source, dst, status, rendered in per_file:
            if status in ("absent", "obsolete") and tool_of(source) not in blocked:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(rendered)
                written.append(source)

    return {
        "cible": str(target_root),
        "classes": classes,
        "local_seul": orphans,
        "outils_bloques": blocked,
        "ecrits": written,
        "examines": len(file_pairs),
        "notice": hooks_notice(agent, scopes, target_root),
        "ignores": ignores,
        "statusline": statusline_state(agent, scopes, target_root, wanted),
        "file_pairs": file_pairs,
        "subs": subs,
    }


def print_report(agent: str, r: dict, apply: bool) -> None:
    classes = r["classes"]
    print(f"install.py [{agent}] : {r['examines']} fichier(s) examines -> {r['cible']}")
    print(f"  identiques   {len(classes['identique'])}")
    for label, key in (
        ("absents", "absent"),
        ("obsoletes", "obsolete"),
        ("conflits", "conflit"),
        ("illisibles", "illisible"),
    ):
        if classes[key]:
            print(f"  {label:<12} {len(classes[key])}  {', '.join(classes[key])}")
    if r["local_seul"]:
        print(f"  local seul   {len(r['local_seul'])}  {', '.join(r['local_seul'])}")
    if r["notice"]:
        print(f"  {r['notice']}")
    for scope in r["ignores"]:
        print(f"  {scope} : non pris en charge pour {agent}, rien d'examine")
    sl = r["statusline"]
    if sl:
        if sl["etat"] == "enregistree":
            print(f"  statusLine   enregistree ({sl['outil']}) dans {sl['fichier']}")
        elif sl["etat"] == "illisible":
            print(f"  statusLine   {sl['fichier']} illisible (JSON invalide)")
        else:
            label = "absente" if sl["etat"] == "absente" else "designe un autre script"
            print(f"  statusLine   {label} dans {sl['fichier']} ; jamais ecrite par ce script.")
            print("    Fragment a fusionner a la main, sans ecraser le reste du fichier :")
            for fragment in sl["fragments"].values():
                text = json.dumps({"statusLine": fragment}, indent=2)
                print("\n".join("      " + line for line in text.splitlines()))
    if apply:
        detail = f"  {', '.join(r['ecrits'])}" if r["ecrits"] else ""
        print(f"  ecrits : {len(r['ecrits'])}{detail}")
    elif classes["absent"] or classes["obsolete"]:
        print("  relancer avec --apply pour ecrire les cas surs")
    if classes["conflit"]:
        print(
            f"  {len(classes['conflit'])} conflit(s) a arbitrer ; outils laisses "
            f"intacts chez {agent} : {', '.join(r['outils_bloques'])}"
        )
    print()


def main() -> int:
    args = parse_args()

    agents = parse_list(args.agent)
    scopes = parse_list(args.scope)
    for label, values, known in (
        ("agent hote", agents, AGENTS),
        ("perimetre", scopes, SCOPES),
    ):
        unknown = [v for v in values if v not in known]
        if unknown:
            print(f"install.py : {label} inconnu : {', '.join(unknown)}", file=sys.stderr)
            return 1
    if not agents:
        print("install.py : aucun agent hote demande", file=sys.stderr)
        return 1
    if args.target is not None and len(agents) != 1:
        print(
            "install.py : --target exige un seul agent hote (--agent claude ou --agent copilot)",
            file=sys.stderr,
        )
        return 1

    if args.tool:
        wanted = set(parse_list(args.tool))
        # Outils connus de tout agent hote : une status line demandee pour
        # Copilot CLI est signalee comme non prise en charge, non comme inconnue.
        known = {
            tool_of(rel)
            for agent in AGENTS
            for rel, _, _ in pairs(agent, scopes_of(agent, scopes), ROOT)
        }
        if wanted - known:
            print(
                f"install.py : outil inconnu : {', '.join(sorted(wanted - known))}",
                file=sys.stderr,
            )
            return 1

    if args.diff:
        # Le diff cite le contenu des fichiers, accents et symboles compris :
        # l'encodage par defaut de la console (cp1252) ferait echouer l'ecriture.
        sys.stdout.reconfigure(encoding="utf-8")
        wanted_path = args.diff.replace("\\", "/")
        found = False
        for agent in agents:
            read_only_args = argparse.Namespace(**{**vars(args), "apply": False})
            r = examine(agent, read_only_args, scopes)
            for source, src, dst in r["file_pairs"]:
                if source == wanted_path:
                    found = True
                    sys.stdout.write(
                        unified(agent, source, src, dst, r["subs"])
                        or f"[{agent}] {source} : aucun ecart\n"
                    )
        if not found:
            print(
                f"install.py : '{args.diff}' hors du perimetre {','.join(scopes)}",
                file=sys.stderr,
            )
            return 1
        return 0

    reports = {agent: examine(agent, args, scopes) for agent in agents}
    conflicts = sum(len(r["classes"]["conflit"]) for r in reports.values())

    if args.json:
        keys = ("cible", "classes", "local_seul", "outils_bloques", "ecrits", "statusline")
        print(
            json.dumps(
                {
                    "perimetres": scopes,
                    "agents": {
                        agent: {k: r[k] for k in keys} for agent, r in reports.items()
                    },
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return 1 if conflicts else 0

    for agent, r in reports.items():
        print_report(agent, r, args.apply)

    if conflicts:
        print(
            f"install.py : {conflicts} conflit(s) a arbitrer (docs/SETUP.md section 2)."
        )
        print("  install.py --diff <chemin> [--agent <nom>] affiche l'ecart d'un fichier.")
        return 1

    print("install.py : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
