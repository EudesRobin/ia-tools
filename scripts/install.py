#!/usr/bin/env python3
"""Merge intelligent du depot vers chaque agent hote (docs/SETUP.md).

Agents hotes pris en charge, dont la racine est notee {AGENT_DIR} :

  claude    ~/.claude     agent installe sous <nom>.md
  copilot   ~/.copilot    agent installe sous <nom>.agent.md

Pour chaque agent hote, classe chaque fichier distribue par ce depot face a sa
cible locale, puis ecrit ce que l'utilisateur a confirme :

  absent      cible inexistante                        -> ecrire le rendu
  identique   rendu == cible                           -> rien
  obsolete    cible == rendu d'une revision anterieure,
              ou source brute non substituee           -> ecrire le rendu
  conflit     ni l'un ni l'autre : edition locale       -> sauvegarder, ecrire le rendu
  local-seul  present seulement en local, dans le dossier
              d'un outil du depot                     -> sauvegarder, supprimer
  retire      outil supprime du depot, present en local
              et egal a une revision anterieure        -> sauvegarder, supprimer

Un outil retire modifie localement, peut-etre porte desormais par un autre
depot, est laisse en place et signale.

Deux commandes. 'audit' (defaut) n'ecrit rien et rend un resume court : une
ligne par agent hote, une ligne par outil a ecrire, sous un identifiant court.
'apply' ecrit les outils confirmes : --all pour tous, --confirm <id>,... pour
ceux-la. Le depot l'emporte : un outil n'admet aucune personnalisation hors des
placeholders, et la version locale d'un conflit est sauvegardee sous
{AGENT_DIR}/.ia-tools-backup/<horodatage>/ puis remplacee par le rendu. Un
outil homonyme cree par l'utilisateur est remplace de meme. L'identifiant
derive de l'etat examine : il change des que la cible change, et 'apply'
refuse tout identifiant perime, sans qu'aucun etat soit stocke. 'apply' refait
l'audit avant et apres ses ecritures. Aucune sortie ne cite le contenu d'un
fichier.

Un outil (une skill, un agent et ses documents) s'ecrit d'un bloc chez un agent
hote. --apply, obsolete, n'ecrit que les outils sans conflit et ne supprime
rien. Chaque agent hote est traite separement.

Le rapport donne l'etat de chaque outil, celui du plus en retard de ses
fichiers : a_jour, a_installer, a_mettre_a_jour, retire, conflit ou illisible ;
apres 'apply', installe, mis_a_jour, supprime ou echec a la place des etats
ecrits. Chaque
ecriture est relue et comparee au rendu : une ecriture impossible ou divergente
est classee en echec, sans interrompre les autres outils.

scripts/validate.py est lance avant tout examen : en echec, 'apply' n'ecrit
rien ; une anomalie d'environnement (code 2, pyyaml absent) est signalee sans
bloquer, l'installation n'exigeant que Python.

Le rendu est la source apres substitution des placeholders {NOM_VARIABLE}
(docs/SETUP.md section 1). La comparaison normalise les fins de ligne ; l'ecriture
recopie les octets du rendu, ce qui preserve celles de l'arbre de travail.

Garde-fou non negociable : les fichiers d'enregistrement de hooks ne sont
jamais ecrits, et settings.json ne l'est que pour sa seule cle statusLine, sur
identifiant confirme par l'utilisateur ; --all ne l'ecrit jamais. L'audit lit
settings.json et propose, quand la cle est absente ou designe un autre script,
une action distincte par status line du depot. 'apply --confirm <id>' installe
alors la status line, sauvegarde settings.json, pose la cle en conservant les
autres et leur ordre, puis relit le fichier. Un settings.json illisible n'est
jamais ecrit.

Un outil peut s'appuyer sur un autre outil du depot (CONVENTIONS.md 1.7) :
la carte des dependances est le tableau de la section « Dependances entre
outils » de README.md. --tool installe aussi les dependances declarees des
outils nommes, de proche en proche.

Une status line est propre a un agent hote, que nomme son dossier source :
statuslines/<agent hote>/<nom>/ s'installe sous {AGENT_DIR}/statuslines/<nom>/.
Seul Claude Code en a aujourd'hui (SCOPE_AGENTS) : le perimetre statusline
n'est examine pour aucun autre agent hote.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell, dont l'encodage par defaut corrompt les caracteres accentues
(voir docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/install.py [audit] [--agent ...] [--scope ...]
                                  [--tool ...] [--target <dossier>] [--json]
        python scripts/install.py apply [--all] [--confirm <id>,...]
                                  [options de l'audit]
--apply (obsolete) ecrit les outils sans conflit ; --diff <chemin> donne la
classe d'un fichier chez chaque agent hote.
Code de sortie : 0 si la validation n'est pas en echec (une validation
impossible en raison d'une anomalie d'environnement ne compte pas comme un
echec) et qu'aucun conflit ni echec d'ecriture ne reste chez aucun agent hote,
1 sinon.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
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

# Carte des dependances entre outils (CONVENTIONS.md 1.7) : tableau place
# sous ce titre dans README.md, colonnes Outil | Depend de | Pour.
DEPENDENCIES_FILE = ROOT / "README.md"
DEPENDENCIES_HEADING = "## Dépendances entre outils"
TOOL_NAME_RE = re.compile(r"`([a-z0-9][a-z0-9-]*)`")

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

COMMANDS = ("audit", "apply")

# Dossier de {AGENT_DIR} ou chaque version locale est sauvegardee avant d'etre
# remplacee.
BACKUP_DIR = ".ia-tools-backup"

# Jamais classe ni ecrit, dans le depot comme en local.
EXCLUDED_DIRS = {".idea", "__pycache__", "plugins", ".git", BACKUP_DIR}
EXCLUDED_NAMES = {"settings.json", "settings.local.json", ".gitignore"}

# Validateur des sources, lance avant tout examen (docs/SETUP.md section 2).
VALIDATOR = ROOT / "scripts" / "validate.py"

# Etat d'un outil : celui du plus en retard de ses fichiers. Libelles affiches,
# dans l'ordre d'affichage, de ce qui appelle une suite a ce qui est a jour.
STATE_LABELS = {
    "conflit": "conflit",
    "echec": "echec ecriture",
    "illisible": "illisible",
    "a_installer": "a installer",
    "a_mettre_a_jour": "a mettre a jour",
    "retire": "retire du depot",
    "installe": "installe",
    "mis_a_jour": "mis a jour",
    "supprime": "supprime",
    "a_jour": "a jour",
}

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


def declared_dependencies(text: str) -> dict[str, list[str]]:
    """Carte des dependances lue dans le texte de README.md : outil -> outils
    dont il depend. Sans section ni ligne de tableau, la carte est vide."""
    deps: dict[str, list[str]] = {}
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == DEPENDENCIES_HEADING
            continue
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        tools = TOOL_NAME_RE.findall(cells[0])
        needed = TOOL_NAME_RE.findall(cells[1])
        # Ligne d'en-tete et separateur : aucun nom entre backticks.
        if len(tools) == 1 and needed:
            deps.setdefault(tools[0], [])
            deps[tools[0]] += [n for n in needed if n not in deps[tools[0]]]
    return deps


def with_dependencies(wanted: set[str], deps: dict[str, list[str]]) -> set[str]:
    """Outils demandes et leurs dependances, de proche en proche ; un cycle
    n'entraine pas de boucle."""
    found = set(wanted)
    pending = list(wanted)
    while pending:
        for needed in deps.get(pending.pop(), []):
            if needed not in found:
                found.add(needed)
                pending.append(needed)
    return found


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
    """Formes normalisees prises par le rendu de ce fichier dans l'historique,
    de la plus recente a la plus ancienne.

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


def retired_tools(agent: str, scopes: list[str], target_root: Path,
                  subs: dict[str, str]) -> tuple[list[str], list[str]]:
    """(fichiers locaux des outils retires restes intacts, noms des outils
    retires modifies localement).

    Un outil retire a eu des fichiers dans l'historique du depot et n'en a plus
    aucun. Il n'est intact que si chacun de ses fichiers locaux egale le rendu
    d'une revision d'un fichier supprime du depot. Sans git, aucun outil n'est
    reconnu comme retire.
    """
    intact, modified = [], []
    for scope in scopes:
        current = {tool_of(rel) for rel, _, _ in pairs(agent, [scope], target_root)}
        for src_rel, dst_rel in scope_pairs(agent, scope):
            log = git_bytes(
                ["log", "--no-renames", "--diff-filter=D", "--name-only", "--format=", "--", src_rel]
            )
            deleted = {
                line.strip() for line in (log or b"").decode("utf-8", errors="replace").splitlines()
                if line.strip()
            }
            names = {tool_of(path) for path in deleted} - current
            dst = target_root / dst_rel
            if not names or not dst.is_dir():
                continue
            by_tool: dict[str, list[Path]] = {}
            for path in sorted(dst.rglob("*")):
                rel = path.relative_to(dst)
                if not path.is_file() or excluded(rel):
                    continue
                name = tool_of(f"{dst_rel}/{rel.as_posix()}")
                if name in names:
                    by_tool.setdefault(name, []).append(rel)

            def was_rendered(rel: Path) -> bool:
                origin = source_rel(agent, src_rel, rel)
                if origin is None or f"{src_rel}/{origin.as_posix()}" not in deleted:
                    return False
                local = read_bytes(dst / rel)
                renders = previous_renders(f"{src_rel}/{origin.as_posix()}", subs)
                return local is not None and normalize(local) in renders

            for name, files in sorted(by_tool.items()):
                if all(was_rendered(rel) for rel in files):
                    intact += [f"{dst_rel}/{rel.as_posix()}" for rel in files]
                else:
                    modified.append(name)
    return intact, modified


def classify(source: str, src: Path, dst: Path, subs: dict[str, str]) -> tuple[str, bytes, bytes | None]:
    """(classe, rendu, contenu local) d'un fichier source face a sa cible."""
    raw = read_bytes(src)
    if raw is None:
        return "illisible", b"", read_bytes(dst)
    rendered = render(raw, subs)
    local = read_bytes(dst)
    if local is None:
        return "absent", rendered, None
    if normalize(local) == normalize(rendered):
        return "identique", rendered, local
    # Copie manuelle sans substitution des placeholders : rien d'edite a la main.
    if normalize(local) == normalize(raw) or normalize(local) in previous_renders(source, subs):
        return "obsolete", rendered, local
    return "conflit", rendered, local


def write_checked(dst: Path, rendered: bytes) -> bool:
    """Ecrit le rendu puis le relit : vrai seulement si la cible lui est identique."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(rendered)
    except OSError:
        return False
    local = read_bytes(dst)
    return local is not None and normalize(local) == normalize(rendered)


def remove_checked(dst: Path) -> bool:
    """Supprime la cible : vrai seulement si elle n'existe plus."""
    try:
        dst.unlink()
    except OSError:
        return False
    return not dst.exists()


def prune_empty(target_root: Path, removed: list[Path]) -> None:
    """Retire les dossiers devenus vides, sans remonter jusqu'au dossier d'un
    perimetre (skills/, agents/, agents/docs/, statuslines/)."""
    for path in removed:
        folder = path.parent
        while len(folder.relative_to(target_root).parts) > 1 and folder.relative_to(
            target_root
        ).as_posix() != "agents/docs":
            try:
                folder.rmdir()
            except OSError:
                break
            folder = folder.parent


def backup(target_root: Path, stamp: str, dst: Path, local: bytes) -> Path | None:
    """Copie la version locale sous {AGENT_DIR}/.ia-tools-backup/<horodatage>/ ;
    None si la copie est impossible, auquel cas la cible n'est pas ecrite."""
    copy = target_root / BACKUP_DIR / stamp / dst.relative_to(target_root)
    try:
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(local)
    except (OSError, ValueError):
        return None
    return copy


def tool_states(per_file: list[dict], failed: list[str], written_tools: set[str],
                resolved: set[str]) -> dict[str, str]:
    """Etat de chaque outil, tire des classes de ses fichiers (STATE_LABELS).
    Un conflit resolu en faveur du depot compte comme un fichier obsolete."""
    by_tool: dict[str, list[str]] = {}
    for f in per_file:
        status = "obsolete" if f["source"] in resolved else f["status"]
        by_tool.setdefault(tool_of(f["source"]), []).append(status)
    failed_tools = {tool_of(source) for source in failed}
    states = {}
    for tool, statuses in by_tool.items():
        written = tool in written_tools
        if "conflit" in statuses:
            state = "conflit"
        elif tool in failed_tools:
            state = "echec"
        elif "illisible" in statuses:
            state = "illisible"
        elif all(s == "identique" for s in statuses):
            state = "a_jour"
        elif all(s == "retire" for s in statuses):
            state = "supprime" if written else "retire"
        elif all(s == "absent" for s in statuses):
            state = "installe" if written else "a_installer"
        else:
            state = "mis_a_jour" if written else "a_mettre_a_jour"
        states[tool] = state
    return states


def run_validation() -> tuple[str, str]:
    """(etat, sortie) de scripts/validate.py : ok, echec, ou indisponible (code 2)."""
    try:
        r = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
    except OSError as e:
        return "indisponible", str(e)
    output = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        return "ok", output
    return ("indisponible" if r.returncode == 2 else "echec"), output


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
        f"depot) ; {target_root / HOOK_REGISTRATION[agent]} n'est pas touche."
    )


def parse_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="install.py",
        description="Merge intelligent du depot vers chaque agent hote (docs/SETUP.md).",
    )
    p.add_argument(
        "command",
        nargs="?",
        choices=COMMANDS,
        default="audit",
        help="audit (defaut, n'ecrit rien), apply",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="apply : ecrire tous les outils ; la version locale d'un conflit est "
             "sauvegardee puis remplacee par la version du depot",
    )
    p.add_argument(
        "--confirm",
        action="append",
        default=[],
        metavar="ID,...",
        help="apply : n'ecrire que ces outils",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="obsolete, ecrit les seuls outils sans conflit : "
             "retire dans une prochaine version MAJEUR",
    )
    p.add_argument(
        "--agent",
        default=",".join(DEFAULT_AGENTS),
        help=f"agents hotes separes par des virgules parmi {','.join(AGENTS)}",
    )
    p.add_argument(
        "--scope",
        default=None,
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
        help="classe d'un fichier (chemin source du depot), par agent hote",
    )
    p.add_argument(
        "--target",
        metavar="DOSSIER",
        help="racine cible a la place de {AGENT_DIR} ; un seul agent hote requis",
    )
    p.add_argument("--json", action="store_true", help="sortie machine")
    args = p.parse_args()
    argv = sys.argv[1:]
    if any(a == "--outil" or a.startswith("--outil=") for a in argv):
        print("install.py : --outil est obsolete, employer --tool", file=sys.stderr)
    # --apply garde son comportement publie : les conflits restent intacts.
    args.keep_conflicts = args.apply
    if args.apply:
        print("install.py : --apply est obsolete, employer 'apply --all'", file=sys.stderr)
        args.command, args.all = "apply", True
    return args


def examine(agent: str, args: argparse.Namespace, scopes: list[str]) -> dict:
    """Classe le perimetre d'un agent hote, sans rien ecrire."""
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
        status, rendered, local = classify(source, src, dst, subs)
        classes[status].append(source)
        per_file.append(
            {"source": source, "dst": dst, "status": status, "rendered": rendered, "local": local}
        )
    # --tool ne vise que des outils du depot : aucun outil retire n'est examine.
    retired, retired_modified = (
        ([], []) if wanted is not None else retired_tools(agent, scopes, target_root, subs)
    )
    for rel, status in [(o, "local_seul") for o in orphans] + [(r, "retire") for r in retired]:
        dst = target_root / rel
        per_file.append(
            {"source": rel, "dst": dst, "status": status, "rendered": b"", "local": read_bytes(dst)}
        )

    return {
        "cible": str(target_root),
        "target_root": target_root,
        "classes": classes,
        "local_seul": orphans,
        "retires": sorted({tool_of(rel) for rel in retired}),
        "retires_modifies": retired_modified,
        "outils_bloques": sorted({tool_of(rel) for rel in classes["conflit"]}),
        "ecrits": [],
        "supprimes": [],
        "cle_enregistree": None,
        "echecs": [],
        "resolus": [],
        "sauvegarde": None,
        "outils": tool_states(per_file, [], set(), set()),
        "examines": len(file_pairs),
        "notice": hooks_notice(agent, scopes, target_root),
        "ignores": ignores,
        "statusline": statusline_state(agent, scopes, target_root, wanted),
        "per_file": per_file,
    }


# Classes d'un fichier qu'apply ecrit ou supprime ; parmi elles, celles qu'il
# supprime.
CHANGING = ("absent", "obsolete", "conflit", "local_seul", "retire")
DELETED = ("local_seul", "retire")


def digest(raw: bytes | None) -> str:
    return "-" if raw is None else hashlib.sha1(normalize(raw)).hexdigest()


def build_actions(reports: dict[str, dict]) -> list[dict]:
    """Une action par outil a ecrire et, quand la cle statusLine est absente ou
    designe un autre script, une par status line a enregistrer. Chacune porte
    un identifiant court tire de l'etat examine : il change des que la cible
    change, si bien qu'un identifiant perime est refuse sans qu'aucun etat soit
    stocke."""
    actions = []
    for agent, r in reports.items():
        by_tool: dict[str, list[dict]] = {}
        for f in r["per_file"]:
            by_tool.setdefault(tool_of(f["source"]), []).append(f)
        for tool, files in sorted(by_tool.items()):
            state = r["outils"][tool]
            if state not in ("a_installer", "a_mettre_a_jour", "retire", "conflit"):
                continue
            changing = [f for f in files if f["status"] in CHANGING]
            key = "|".join(
                [agent, tool]
                + [f"{f['source']}:{f['status']}:{digest(f['local'])}" for f in changing]
            )
            actions.append({
                "type": "outil", "agent": agent, "outil": tool, "etat": state,
                "fichiers": len(changing),
                "editions": [f["source"] for f in changing if f["status"] == "conflit"],
                "suppressions": [f["source"] for f in changing if f["status"] in DELETED],
                "key": key,
            })
        sl = r["statusline"]
        if sl and sl["etat"] in ("absente", "autre"):
            current = digest(read_bytes(Path(sl["fichier"])))
            for name, fragment in sl["fragments"].items():
                actions.append({
                    "type": "statusline", "agent": agent, "outil": name, "etat": sl["etat"],
                    "fichier": sl["fichier"], "cle": fragment,
                    "key": f"{agent}|statusLine|{name}|{current}",
                })
    for length in (4, 6, 8, 40):
        ids = [hashlib.sha1(a["key"].encode("utf-8")).hexdigest()[:length] for a in actions]
        if len(set(ids)) == len(ids):
            break
    for action, ident in zip(actions, ids):
        action["id"] = ident
    return actions


def parse_confirm(values: list[str], actions: list[dict]) -> tuple[set[str], str | None]:
    """Identifiants confirmes, ou un message d'erreur. Un identifiant inconnu ou
    perime fait tout refuser : rien n'est ecrit."""
    known = {a["id"] for a in actions}
    chosen = set()
    for ident in (i for value in values for i in parse_list(value)):
        if ident not in known:
            return set(), f"identifiant inconnu ou perime : {ident} ; relancer l'audit"
        chosen.add(ident)
    keys = [a["agent"] for a in actions if a["type"] == "statusline" and a["id"] in chosen]
    if len(keys) != len(set(keys)):
        return set(), "une seule status line par agent hote peut etre enregistree"
    return chosen, None


def register_statusline(r: dict, action: dict, stamp: str) -> bool:
    """Pose la cle statusLine dans settings.json, apres sauvegarde du fichier,
    en conservant les autres cles et leur ordre, puis relit le fichier : vrai
    seulement si la cle relue est celle attendue."""
    settings = Path(action["fichier"])
    raw = read_bytes(settings)
    try:
        data = json.loads(raw.decode("utf-8-sig")) if raw is not None else {}
    except (ValueError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if raw is not None:
        if backup(r["target_root"], stamp, settings, raw) is None:
            return False
        r["sauvegarde"] = str(r["target_root"] / BACKUP_DIR / stamp)
    data["statusLine"] = action["cle"]
    try:
        settings.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return json.loads(settings.read_text(encoding="utf-8")).get("statusLine") == action["cle"]
    except (OSError, ValueError):
        return False


def apply_agent(agent: str, r: dict, actions: list[dict], chosen: set[str],
                write_all: bool, keep_conflicts: bool, stamp: str) -> None:
    """Ecrit, chez un agent hote, les outils confirmes, et supprime leurs
    fichiers en local seul et les fichiers des outils retires. La version
    locale d'un conflit ou d'un fichier supprime est d'abord sauvegardee ; une
    sauvegarde impossible laisse la cible intacte et compte comme un echec.
    Avec keep_conflicts (--apply), --all laisse de cote les outils en conflit
    et ne supprime rien. Une status line dont la cle est confirmee est installee,
    puis enregistree."""
    mine = [a for a in actions if a["agent"] == agent]
    keys = [a for a in mine if a["type"] == "statusline" and a["id"] in chosen]
    tools = {
        a["outil"] for a in mine
        if a["type"] == "outil" and (
            a["id"] in chosen or (write_all and not (keep_conflicts and a["editions"]))
        )
    } | {a["outil"] for a in keys}
    written, removed, failed, resolved = [], [], [], []
    for f in r["per_file"]:
        source, dst, status = f["source"], f["dst"], f["status"]
        if tool_of(source) not in tools or status not in CHANGING:
            continue
        if status in DELETED and keep_conflicts:
            continue
        if status in DELETED + ("conflit",):
            if backup(r["target_root"], stamp, dst, f["local"] or b"") is None:
                failed.append(source)
                continue
            r["sauvegarde"] = str(r["target_root"] / BACKUP_DIR / stamp)
        if status in DELETED:
            (removed if remove_checked(dst) else failed).append(source)
            continue
        if status == "conflit":
            resolved.append(source)
        (written if write_checked(dst, f["rendered"]) else failed).append(source)
    prune_empty(r["target_root"], [r["target_root"] / s for s in removed])

    r["ecrits"], r["supprimes"], r["echecs"], r["resolus"] = written, removed, failed, resolved
    touched = {tool_of(s) for s in written + removed}
    r["outils"] = tool_states(r["per_file"], failed, touched, set(resolved))
    unresolved = [s for s in r["classes"]["conflit"] if s not in resolved]
    r["outils_bloques"] = sorted({tool_of(s) for s in unresolved})

    for action in keys:
        if any(tool_of(s) == action["outil"] for s in failed):
            continue
        if register_statusline(r, action, stamp):
            r["cle_enregistree"] = action["outil"]
        else:
            r["echecs"].append(f"{action['fichier']} (cle statusLine)")


def command_options(args: argparse.Namespace) -> str:
    """Options de la commande en cours, a reprendre dans la commande proposee."""
    opts = []
    if args.agent != ",".join(DEFAULT_AGENTS):
        opts.append(f"--agent {args.agent}")
    if args.scope is not None:
        opts.append(f"--scope {args.scope}")
    if args.tool:
        opts.append(f"--tool {args.tool}")
    if args.target is not None:
        opts.append(f'--target "{args.target}"')
    return "".join(f" {o}" for o in opts)


def shown_deletions(action: dict) -> list[str]:
    """Suppressions affichees : chaque fichier, ou le dossier d'un outil retire."""
    if action["etat"] != "retire":
        return action["suppressions"]
    shown = []
    for source in action["suppressions"]:
        parts = source.split("/")
        depth = 3 if parts[:2] == ["agents", "docs"] else 2
        root = "/".join(parts[:depth]) + ("/" if len(parts) > depth else "")
        if root not in shown:
            shown.append(root)
    return shown


def print_summary(reports: dict[str, dict], actions: list[dict], args: argparse.Namespace) -> None:
    """Resume court : une ligne par agent hote, une ligne par outil a ecrire,
    jamais le contenu d'un fichier."""
    for agent, r in reports.items():
        counts: dict[str, int] = {}
        for state in r["outils"].values():
            counts[state] = counts.get(state, 0) + 1
        detail = ", ".join(
            f"{counts[s]} {label}" for s, label in STATE_LABELS.items() if s in counts
        )
        print(f"{agent:<8} {r['cible']} : {len(r['outils'])} outil(s) ; {detail or 'rien a examiner'}")

    tool_actions = [a for a in actions if a["type"] == "outil"]
    keys = [a for a in actions if a["type"] == "statusline"]
    if tool_actions:
        print("\na faire (--all, ou --confirm <id>,...) :")
        for a in tool_actions:
            label = STATE_LABELS[a["etat"]]
            print(f"  {a['id']}  {a['agent']:<8} {a['outil']}  {label} ({a['fichiers']} fichier(s))")
            for source in a["editions"]:
                print(f"        edition locale, sauvegardee puis remplacee : {source}")
            for source in shown_deletions(a):
                print(f"        supprime apres sauvegarde : {source}")
    if keys:
        print("\ncle statusLine, sur accord explicite de l'utilisateur, jamais incluse dans --all :")
        for a in keys:
            if a["etat"] == "absente":
                label, verb = "cle absente", "ecrite"
            else:
                label, verb = "cle designant un autre script", "remplacee"
            print(f"  {a['id']}  {a['agent']:<8} {a['outil']}  {label}")
            print(f"        {verb} dans {a['fichier']}, sauvegarde au prealable")

    notes = []
    for agent, r in reports.items():
        notes += [f"{agent} : illisible : {s}" for s in r["classes"]["illisible"]]
        notes += [f"{agent} : ecriture impossible ou divergente : {s}" for s in r["echecs"]]
        notes += [
            f"{agent} : outil retire du depot, modifie localement, laisse en place : {name}"
            for name in r["retires_modifies"]
        ]
        if args.scope is not None:
            if r["notice"]:
                notes.append(f"{agent} : {r['notice']}")
            notes += [f"{agent} : {s} non pris en charge, rien d'examine" for s in r["ignores"]]
        sl = r["statusline"]
        if sl and sl["etat"] == "illisible":
            notes.append(
                f"{agent} : statusLine illisible, {sl['fichier']} n'est pas du JSON valide ; "
                "rien n'y sera ecrit"
            )
    if notes:
        print("\npour information :")
        for note in notes:
            print(f"  {note}")

    command = f"python scripts/install.py apply{command_options(args)}"
    ident = keys[0]["id"] if len(keys) == 1 else "<id>"
    if tool_actions:
        print(f"\ncommande : {command} --all")
        if keys:
            print(f"cle statusLine, sur accord explicite : ajouter --confirm {ident}")
    elif keys:
        print(f"\ncommande, sur accord explicite : {command} --confirm {ident}")
    else:
        print("\nrien a installer ni a mettre a jour.")


def public(action: dict) -> dict:
    return {k: v for k, v in action.items() if k != "key"}


def main() -> int:
    args = parse_args()

    agents = parse_list(args.agent)
    scopes = parse_list(args.scope) if args.scope is not None else list(DEFAULT_SCOPES)
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
    if args.command == "apply" and not (args.all or args.confirm):
        print("install.py : apply exige --all ou --confirm <id>,...", file=sys.stderr)
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
        text = DEPENDENCIES_FILE.read_text(encoding="utf-8") if DEPENDENCIES_FILE.is_file() else ""
        expanded = with_dependencies(wanted, declared_dependencies(text))
        added = sorted(expanded - wanted)
        if added:
            args.tool = ",".join(sorted(expanded))
    else:
        added = []

    if args.diff:
        reports = {agent: examine(agent, args, scopes) for agent in agents}
        return show_diff_summary(args.diff, reports, build_actions(reports), scopes)

    validation, validation_output = run_validation()
    if validation != "ok":
        print(validation_output, file=sys.stderr)
    if args.command == "apply" and validation == "echec":
        print("install.py : validation (scripts/validate.py) en echec : rien n'est ecrit ;")
        print("  corriger les sources avant d'installer.")
        return 1

    reports = {agent: examine(agent, args, scopes) for agent in agents}
    actions = build_actions(reports)
    remaining = actions

    if args.command == "apply":
        chosen, error = parse_confirm(args.confirm, actions)
        if error:
            print(f"install.py : {error} ; rien n'est ecrit", file=sys.stderr)
            return 1
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for agent, r in reports.items():
            apply_agent(agent, r, actions, chosen, args.all, args.keep_conflicts, stamp)
        after = {agent: examine(agent, args, scopes) for agent in agents}
        remaining = build_actions(after)
        for agent, r in after.items():
            r["echecs"] = reports[agent]["echecs"]

    failures = sum(len(r["echecs"]) for r in reports.values())
    conflicts = sum(len(a["editions"]) for a in remaining if a["type"] == "outil")
    red = bool(conflicts or failures or validation == "echec")

    if args.json:
        keys = (
            "cible", "outils", "classes", "local_seul", "retires", "retires_modifies",
            "outils_bloques", "ecrits", "supprimes", "echecs", "resolus", "sauvegarde",
            "statusline", "cle_enregistree",
        )
        print(
            json.dumps(
                {
                    "validation": validation,
                    "perimetres": scopes,
                    "dependances_ajoutees": added,
                    "agents": {
                        agent: {k: r[k] for k in keys} for agent, r in reports.items()
                    },
                    "actions": [public(a) for a in remaining],
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return 1 if red else 0

    if validation == "ok":
        print("install.py : validation OK")
    elif validation == "indisponible":
        print("install.py : validation impossible (anomalie d'environnement, voir stderr), poursuivie sans elle")
    else:
        print("install.py : validation (scripts/validate.py) en echec : apply n'ecrira rien")
    if added:
        print(f"install.py : dependances ajoutees : {', '.join(added)}")
    if args.command == "apply":
        for agent, r in reports.items():
            line = f"{agent} : {len(r['ecrits'])} fichier(s) ecrit(s) et verifie(s)"
            if r["resolus"]:
                line += f", dont {len(r['resolus'])} edition(s) locale(s) remplacee(s)"
            if r["supprimes"]:
                line += f" ; {len(r['supprimes'])} fichier(s) supprime(s)"
            if r["cle_enregistree"]:
                line += f" ; cle statusLine enregistree : {r['cle_enregistree']}"
            if r["sauvegarde"]:
                line += f" ; sauvegarde : {r['sauvegarde']}"
            print(line)
        print("\napres apply :")
        print_summary(after, remaining, args)
    else:
        print()
        print_summary(reports, remaining, args)
    return 1 if red else 0


def show_diff_summary(path: str, reports: dict[str, dict], actions: list[dict], scopes: list[str]) -> int:
    """--diff <chemin> : classe du fichier chez chaque agent hote et
    identifiant de son outil ; jamais le contenu."""
    wanted = path.replace("\\", "/")
    found = False
    for agent, r in reports.items():
        for f in r["per_file"]:
            if f["source"] != wanted:
                continue
            found = True
            action = next(
                (a for a in actions if a["type"] == "outil" and a["agent"] == agent
                 and a["outil"] == tool_of(wanted)),
                None,
            )
            ident = f", outil {action['id']}" if action else ""
            print(f"[{agent}] {wanted} : {f['status']}{ident}")
    if not found:
        print(f"install.py : '{path}' hors du perimetre {','.join(scopes)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
