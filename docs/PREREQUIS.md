# PREREQUIS — outils système (hors Claude)

Outils **hôte** supposés présents par certaines skills et par l'outillage du
dépôt. Indépendants de l'installation des outils Claude (voir
[SETUP.md](SETUP.md)) : ce sont des binaires/paquets système, pas des
fichiers copiés vers `~/.claude/`.

Enregistré dans la table de routage : [DOC_MAP.md](DOC_MAP.md).

**Étape optionnelle**, à proposer sur un environnement neuf ou incomplet. Ne
rien installer sans accord : d'abord **vérifier** ce qui manque, en dresser la
liste, puis demander l'accord de l'utilisateur.

Commandes ci-dessous pour **Windows** (`winget`, PowerShell). Adapter le
gestionnaire de paquets sur un autre système.

## Récapitulatif

| Outil              | Requis par                                  | Vérifier                         | Installer (Windows)                          |
|--------------------|---------------------------------------------|----------------------------------|----------------------------------------------|
| Python 3 (PATH)    | `scripts/` (contribution au dépôt)          | `python --version`               | `winget install Python.Python.3.13` (dernière 3.x) |
| Bibliothèques Python | `scripts/validate.py`                     | `pip show <nom>`                 | voir [Bibliothèques Python](#bibliothèques-python) |
| `adb` (platform-tools) | `clean-android-tv`                      | `adb version`                    | `winget install Google.PlatformTools`        |
| PowerShell 7 (`pwsh`) | hook `validate-tool` (contribution au dépôt) | `pwsh --version`             | `winget install Microsoft.PowerShell`        |

## Procédure

1. Vérifier chaque outil (colonne « Vérifier »). Lister ce qui manque.
2. Demander l'accord avant d'installer. Ne jamais réinstaller un outil présent.
3. Après l'installation d'un binaire (Python, adb, pwsh) : rouvrir le terminal
   pour rafraîchir le PATH, puis revérifier.

## Détails

### Python

Dernière version 3.x (pas de version imposée). L'identifiant winget contient le
numéro de version : `winget search Python.Python` pour trouver la version
mineure la plus récente, sinon `Python.Python.3.13`. Cocher
`Add python.exe to PATH` en cas d'installation manuelle : les scripts
supposent `python` accessible sans chemin absolu.

### Bibliothèques Python

```powershell
pip install pyyaml
```

| Bibliothèque       | Usage                                              |
|--------------------|----------------------------------------------------|
| `pyyaml`           | `scripts/validate.py` — lecture stricte du front-matter. Requis pour **contribuer** à ce dépôt, pas pour utiliser les outils installés |

### adb (platform-tools)

`winget install Google.PlatformTools` dépose `platform-tools` sous
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\` et ajoute ce dossier au PATH. Aucun
alias n'est créé dans `WinGet\Links` : un terminal ouvert avant l'installation
ne voit pas `adb` et doit être rouvert.

**Un seul adb sur le PATH.** Une installation manuelle antérieure de
`platform-tools` laisse un second binaire, souvent d'une version différente, ce
qui provoque une erreur de correspondance entre client et serveur adb. Contrôler
avec `where.exe adb` et retirer l'entrée surnuméraire.

### PowerShell 7

Requis par le hook [`validate-tool`](../hooks/validate-tool/HOOK.md), qui ne
s'active que dans une session ouverte sur ce dépôt. Sans objet pour qui se
contente d'utiliser les outils installés.

## Encodage de la console

La console PowerShell corrompt les accents en sortie Python. Avant de lancer un
script qui écrit de l'UTF-8 sur la console :

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
```

Ou écrire la sortie dans un fichier UTF-8.
