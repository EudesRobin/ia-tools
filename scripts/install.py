#!/usr/bin/env python3
"""Merge intelligent du depot vers ~/.claude/ (docs/SETUP.md).

Classe chaque fichier distribue par ce depot face a sa cible locale, applique
les cas surs sur demande, et laisse a la session les seuls conflits :

  absent      cible inexistante                        -> ecrire le rendu
  identique   rendu == cible                           -> rien
  obsolete    cible == rendu d'une revision anterieure  -> ecrire le rendu
  conflit     ni l'un ni l'autre : edition locale       -> arbitrage humain
  local-seul  present seulement en local                -> liste, jamais supprime

Un outil (une skill, un agent et ses documents) s'installe d'un bloc : si l'un
de ses fichiers est en conflit, aucun de ses fichiers n'est ecrit. Un outil
homonyme cree par l'utilisateur n'est donc jamais complete ni modifie.

Le rendu est la source apres substitution des placeholders <NOM_VARIABLE>
(docs/SETUP.md section 1). La comparaison normalise les fins de ligne ; l'ecriture
recopie les octets du rendu, ce qui preserve celles de l'arbre de travail.

Garde-fou non negociable : ~/.claude/settings.json n'est jamais ecrit. Une
entree de hook a fusionner est affichee, pas appliquee.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell, dont l'encodage par defaut corrompt les caracteres accentues
(voir docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/install.py [--apply] [--scope ...] [--outil ...]
                                  [--diff <chemin>] [--target <dossier>] [--json]
Code de sortie : 0 si aucun conflit ne reste, 1 sinon.
"""

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Perimetres et paires source -> cible (docs/SETUP.md section 1).
# Un dossier source est recopie recursivement sous le dossier cible.
SCOPES = {
    "skills": [("skills", "skills")],
    "agents": [("agents", "agents")],
    "hooks": [],  # aucun hook distribue : validate-tool est local au depot
}
DEFAULT_SCOPES = ["skills", "agents", "hooks"]

# Jamais classe ni ecrit, dans le depot comme en local.
EXCLUDED_DIRS = {".idea", "__pycache__", "plugins", ".git"}
EXCLUDED_NAMES = {"settings.json", "settings.local.json", ".gitignore"}

# Profondeur d'historique exploree pour reconnaitre une installation obsolete.
HISTORY_MAX_REVS = 60


def variables() -> dict[str, str]:
    """Variables substituees a l'installation (docs/SETUP.md section 1).

    Seule difference legitime entre un fichier du depot et sa cible. Aucune
    aujourd'hui ; une variable ajoutee se declare ici, avec une valeur derivee
    de l'environnement et jamais un chemin local en dur (CONVENTIONS.md
    section 1.2).
    """
    return {}


def tool_of(rel: str) -> str:
    """Nom de l'outil auquel appartient un chemin : skills/<nom>/..., agents/<nom>.md
    ou agents/docs/<nom>/..."""
    parts = rel.split("/")
    if parts[0] == "agents":
        return parts[2] if parts[1] == "docs" and len(parts) > 2 else parts[1].removesuffix(".md")
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


def previous_renders(source_rel: str, subs: dict[str, str]) -> list[bytes]:
    """Formes normalisees prises par le rendu de ce fichier dans l'historique."""
    log = git_bytes(
        ["log", f"-{HISTORY_MAX_REVS}", "--format=%H", "--", source_rel]
    )
    if not log:
        return []
    formes = []
    for rev in log.decode("utf-8", errors="replace").split():
        blob = git_bytes(["show", f"{rev}:{source_rel}"])
        if blob is None:
            continue
        formes.append(normalize(render(blob, subs)))
    return formes


def pairs(scopes: list[str], target_root: Path) -> list[tuple[str, Path, Path]]:
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
                out.append((f"{src_rel}/{rel.as_posix()}", path, dst / rel))
    return out


def local_only(scopes: list[str], target_root: Path) -> list[str]:
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
                if excluded(rel) or (src / rel).is_file():
                    continue
                out.append(f"{dst_rel}/{rel.as_posix()}")
    return out


def classify(
    source_rel: str, src: Path, dst: Path, subs: dict[str, str]
) -> tuple[str, bytes]:
    raw = read_bytes(src)
    if raw is None:
        return "illisible", b""
    rendu = render(raw, subs)
    local = read_bytes(dst)
    if local is None:
        return "absent", rendu
    if normalize(local) == normalize(rendu):
        return "identique", rendu
    if normalize(local) in previous_renders(source_rel, subs):
        return "obsolete", rendu
    return "conflit", rendu


def unified(source_rel: str, src: Path, dst: Path, subs: dict[str, str]) -> str:
    rendu = render(read_bytes(src) or b"", subs)
    local = read_bytes(dst) or b""
    return "".join(
        difflib.unified_diff(
            normalize(local).decode("utf-8", errors="replace").splitlines(True),
            normalize(rendu).decode("utf-8", errors="replace").splitlines(True),
            fromfile=f"local/{dst.name}",
            tofile=f"depot/{source_rel}",
        )
    )


def hooks_notice(scopes: list[str], target_root: Path) -> str | None:
    """settings.json n'est jamais ecrit : afficher ce qui resterait a faire."""
    if "hooks" not in scopes or SCOPES["hooks"]:
        return None
    return (
        "hooks : aucun hook distribue par ce depot (validate-tool est local au "
        f"depot).\n  {target_root / 'settings.json'} n'est pas touche."
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Merge intelligent du depot vers ~/.claude/ (docs/SETUP.md).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="ecrire les cas surs (absent, obsolete) ; rien pour un outil en conflit",
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
        help="afficher le diff unifie d'un fichier (chemin source du depot)",
    )
    p.add_argument(
        "--target",
        metavar="DOSSIER",
        default=str(Path.home() / ".claude"),
        help="racine cible (defaut : ~/.claude)",
    )
    p.add_argument("--json", action="store_true", help="sortie machine")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
    inconnus = [s for s in scopes if s not in SCOPES]
    if inconnus:
        print(
            f"install.py : perimetre inconnu : {', '.join(inconnus)}", file=sys.stderr
        )
        return 1

    target_root = Path(args.target).expanduser().resolve()
    subs = variables()
    couples = pairs(scopes, target_root)
    orphelins = local_only(scopes, target_root)

    if args.outil:
        voulus = {o.strip() for o in args.outil.split(",") if o.strip()}
        connus = {tool_of(rel) for rel, _, _ in couples}
        if voulus - connus:
            print(
                f"install.py : outil inconnu : {', '.join(sorted(voulus - connus))}",
                file=sys.stderr,
            )
            return 1
        couples = [c for c in couples if tool_of(c[0]) in voulus]
        orphelins = [o for o in orphelins if tool_of(o) in voulus]

    if args.diff:
        vise = args.diff.replace("\\", "/")
        for source_rel, src, dst in couples:
            if source_rel == vise:
                sys.stdout.write(
                    unified(source_rel, src, dst, subs)
                    or f"{source_rel} : aucun ecart\n"
                )
                return 0
        print(
            f"install.py : '{args.diff}' hors du perimetre {','.join(scopes)}",
            file=sys.stderr,
        )
        return 1

    classes: dict[str, list[str]] = {
        "absent": [],
        "identique": [],
        "obsolete": [],
        "conflit": [],
        "illisible": [],
    }
    ecrits: list[str] = []

    classes_par_fichier = []
    for source_rel, src, dst in couples:
        classe, rendu = classify(source_rel, src, dst, subs)
        classes[classe].append(source_rel)
        classes_par_fichier.append((source_rel, dst, classe, rendu))

    conflits = classes["conflit"]
    bloques = sorted({tool_of(rel) for rel in conflits})

    if args.apply:
        for source_rel, dst, classe, rendu in classes_par_fichier:
            if classe in ("absent", "obsolete") and tool_of(source_rel) not in bloques:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(rendu)
                ecrits.append(source_rel)

    if args.json:
        print(
            json.dumps(
                {
                    "cible": str(target_root),
                    "perimetres": scopes,
                    "classes": classes,
                    "local_seul": orphelins,
                    "outils_bloques": bloques,
                    "ecrits": ecrits,
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return 1 if conflits else 0

    print(f"install.py : {len(couples)} fichier(s) examines -> {target_root}")
    print(f"  identiques   {len(classes['identique'])}")
    for libelle, cle in (
        ("absents", "absent"),
        ("obsoletes", "obsolete"),
        ("conflits", "conflit"),
        ("illisibles", "illisible"),
    ):
        if classes[cle]:
            print(f"  {libelle:<12} {len(classes[cle])}  {', '.join(classes[cle])}")
    if orphelins:
        print(f"  local seul   {len(orphelins)}  {', '.join(orphelins)}")

    notice = hooks_notice(scopes, target_root)
    if notice:
        print(f"\n{notice}")

    if args.apply:
        detail = f"  {', '.join(ecrits)}" if ecrits else ""
        print(f"\n  ecrits : {len(ecrits)}{detail}")
    elif classes["absent"] or classes["obsolete"]:
        print("\n  relancer avec --apply pour ecrire les cas surs")

    if conflits:
        print(
            f"\ninstall.py : {len(conflits)} conflit(s) a arbitrer "
            "(docs/SETUP.md section 2)."
        )
        print(
            "  outils laisses intacts, aucun de leurs fichiers n'est ecrit : "
            f"{', '.join(bloques)}"
        )
        print("  install.py --diff <chemin> affiche l'ecart d'un fichier.")
        return 1

    print("\ninstall.py : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
