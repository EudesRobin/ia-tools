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
  local-seul  present seulement en local                -> liste, jamais supprime

Un outil (une skill, un agent et ses documents) s'installe d'un bloc chez un
agent hote : si l'un de ses fichiers y est en conflit, aucun de ses fichiers n'y
est ecrit. Un outil homonyme cree par l'utilisateur n'est donc jamais complete
ni modifie. Chaque agent hote est traite separement.

Le rendu est la source apres substitution des placeholders {NOM_VARIABLE}
(docs/SETUP.md section 1). La comparaison normalise les fins de ligne ; l'ecriture
recopie les octets du rendu, ce qui preserve celles de l'arbre de travail.

Garde-fou non negociable : le settings.json d'un agent hote et ses fichiers
d'enregistrement de hooks ne sont jamais ecrits. Ce qui reste a fusionner est
affiche, pas applique.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell, dont l'encodage par defaut corrompt les caracteres accentues
(voir docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/install.py [--apply] [--agent ...] [--scope ...]
                                  [--outil ...] [--diff <chemin>]
                                  [--target <dossier>] [--json]
Code de sortie : 0 si aucun conflit ne reste chez aucun agent hote, 1 sinon.
"""

import argparse
import difflib
import json
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
# Un dossier source est recopie recursivement sous le dossier cible.
SCOPES = {
    "skills": [("skills", "skills")],
    "agents": [("agents", "agents")],
    "hooks": [],  # aucun hook distribue : validate-tool est local au depot
}
DEFAULT_SCOPES = ["skills", "agents", "hooks"]

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
    agents/<nom>.md, agents/<nom>.agent.md ou agents/docs/<nom>/..."""
    parts = rel.split("/")
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
    """Formes normalisees prises par le rendu de ce fichier dans l'historique."""
    log = git_bytes(["log", f"-{HISTORY_MAX_REVS}", "--format=%H", "--", source])
    if not log:
        return []
    formes = []
    for rev in log.decode("utf-8", errors="replace").split():
        blob = git_bytes(["show", f"{rev}:{source}"])
        if blob is None:
            continue
        formes.append(normalize(render(blob, subs)))
    return formes


def pairs(agent: str, scopes: list[str], target_root: Path) -> list[tuple[str, Path, Path]]:
    """(chemin source affiche, source, cible) pour tout le perimetre demande."""
    out = []
    for scope in scopes:
        for src_rel, dst_rel in SCOPES[scope]:
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
    """Fichiers presents seulement en local. Listes, jamais supprimes."""
    out = []
    for scope in scopes:
        for src_rel, dst_rel in SCOPES[scope]:
            src, dst = ROOT / src_rel, target_root / dst_rel
            if not src.is_dir() or not dst.is_dir():
                continue
            for path in sorted(dst.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(dst)
                if excluded(rel):
                    continue
                origine = source_rel(agent, src_rel, rel)
                if origine is not None and (src / origine).is_file():
                    continue
                out.append(f"{dst_rel}/{rel.as_posix()}")
    return out


def classify(source: str, src: Path, dst: Path, subs: dict[str, str]) -> tuple[str, bytes]:
    raw = read_bytes(src)
    if raw is None:
        return "illisible", b""
    rendu = render(raw, subs)
    local = read_bytes(dst)
    if local is None:
        return "absent", rendu
    if normalize(local) == normalize(rendu):
        return "identique", rendu
    if normalize(local) in previous_renders(source, subs):
        return "obsolete", rendu
    return "conflit", rendu


def unified(agent: str, source: str, src: Path, dst: Path, subs: dict[str, str]) -> str:
    rendu = render(read_bytes(src) or b"", subs)
    local = read_bytes(dst) or b""
    return "".join(
        difflib.unified_diff(
            normalize(local).decode("utf-8", errors="replace").splitlines(True),
            normalize(rendu).decode("utf-8", errors="replace").splitlines(True),
            fromfile=f"{agent}/local/{dst.name}",
            tofile=f"depot/{source}",
        )
    )


def hooks_notice(agent: str, scopes: list[str], target_root: Path) -> str | None:
    """L'enregistrement des hooks n'est jamais ecrit : afficher ce qui resterait a faire."""
    if "hooks" not in scopes or SCOPES["hooks"]:
        return None
    return (
        "hooks : aucun hook distribue par ce depot (validate-tool est local au "
        f"depot).\n  {target_root / HOOK_REGISTRATION[agent]} n'est pas touche."
    )


def parse_list(valeur: str) -> list[str]:
    return [v.strip() for v in valeur.split(",") if v.strip()]


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
        "--outil",
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
    return p.parse_args()


def examine(agent: str, args: argparse.Namespace, scopes: list[str]) -> dict:
    """Classe, et ecrit si --apply, le perimetre d'un agent hote."""
    target_given = args.target is not None
    racine = args.target if target_given else AGENTS[agent]["root"]
    target_root = Path(racine).expanduser().resolve()
    subs = variables(agent, target_root, target_given)
    couples = pairs(agent, scopes, target_root)
    orphelins = local_only(agent, scopes, target_root)

    if args.outil:
        voulus = set(parse_list(args.outil))
        couples = [c for c in couples if tool_of(c[0]) in voulus]
        orphelins = [o for o in orphelins if tool_of(o) in voulus]

    classes: dict[str, list[str]] = {
        "absent": [],
        "identique": [],
        "obsolete": [],
        "conflit": [],
        "illisible": [],
    }
    par_fichier = []
    for source, src, dst in couples:
        classe, rendu = classify(source, src, dst, subs)
        classes[classe].append(source)
        par_fichier.append((source, dst, classe, rendu))

    bloques = sorted({tool_of(rel) for rel in classes["conflit"]})
    ecrits: list[str] = []
    if args.apply:
        for source, dst, classe, rendu in par_fichier:
            if classe in ("absent", "obsolete") and tool_of(source) not in bloques:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(rendu)
                ecrits.append(source)

    return {
        "cible": str(target_root),
        "classes": classes,
        "local_seul": orphelins,
        "outils_bloques": bloques,
        "ecrits": ecrits,
        "examines": len(couples),
        "notice": hooks_notice(agent, scopes, target_root),
        "couples": couples,
        "subs": subs,
    }


def print_report(agent: str, r: dict, apply: bool) -> None:
    classes = r["classes"]
    print(f"install.py [{agent}] : {r['examines']} fichier(s) examines -> {r['cible']}")
    print(f"  identiques   {len(classes['identique'])}")
    for libelle, cle in (
        ("absents", "absent"),
        ("obsoletes", "obsolete"),
        ("conflits", "conflit"),
        ("illisibles", "illisible"),
    ):
        if classes[cle]:
            print(f"  {libelle:<12} {len(classes[cle])}  {', '.join(classes[cle])}")
    if r["local_seul"]:
        print(f"  local seul   {len(r['local_seul'])}  {', '.join(r['local_seul'])}")
    if r["notice"]:
        print(f"  {r['notice']}")
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
    for libelle, valeurs, connus in (
        ("agent hote", agents, AGENTS),
        ("perimetre", scopes, SCOPES),
    ):
        inconnus = [v for v in valeurs if v not in connus]
        if inconnus:
            print(f"install.py : {libelle} inconnu : {', '.join(inconnus)}", file=sys.stderr)
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

    if args.outil:
        voulus = set(parse_list(args.outil))
        connus = {tool_of(rel) for rel, _, _ in pairs(agents[0], scopes, ROOT)}
        if voulus - connus:
            print(
                f"install.py : outil inconnu : {', '.join(sorted(voulus - connus))}",
                file=sys.stderr,
            )
            return 1

    if args.diff:
        vise = args.diff.replace("\\", "/")
        trouve = False
        for agent in agents:
            lecture = argparse.Namespace(**{**vars(args), "apply": False})
            r = examine(agent, lecture, scopes)
            for source, src, dst in r["couples"]:
                if source == vise:
                    trouve = True
                    sys.stdout.write(
                        unified(agent, source, src, dst, r["subs"])
                        or f"[{agent}] {source} : aucun ecart\n"
                    )
        if not trouve:
            print(
                f"install.py : '{args.diff}' hors du perimetre {','.join(scopes)}",
                file=sys.stderr,
            )
            return 1
        return 0

    rapports = {agent: examine(agent, args, scopes) for agent in agents}
    conflits = sum(len(r["classes"]["conflit"]) for r in rapports.values())

    if args.json:
        cles = ("cible", "classes", "local_seul", "outils_bloques", "ecrits")
        print(
            json.dumps(
                {
                    "perimetres": scopes,
                    "agents": {
                        agent: {k: r[k] for k in cles} for agent, r in rapports.items()
                    },
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return 1 if conflits else 0

    for agent, r in rapports.items():
        print_report(agent, r, args.apply)

    if conflits:
        print(
            f"install.py : {conflits} conflit(s) a arbitrer (docs/SETUP.md section 2)."
        )
        print("  install.py --diff <chemin> [--agent <nom>] affiche l'ecart d'un fichier.")
        return 1

    print("install.py : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
