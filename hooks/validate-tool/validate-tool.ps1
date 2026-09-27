#Requires -Version 7
<#
    Hook Stop — lance scripts/validate.py en fin de tour et empeche de rendre la
    main tant qu'il est rouge.

    Contrairement aux hooks distribues (voir docs/CONVENTIONS.md section 3.2),
    celui-ci bloque volontairement : c'est son objet meme. Il est enregistre
    localement au depot, jamais dans la configuration globale d'un agent hote.

    Contrat commun a Claude Code et a Copilot CLI (CONVENTIONS.md section 3.2) :
      - payload JSON sur stdin (cwd, stop_hook_active) ;
      - code 0 sans sortie : rien a signaler, le tour se termine ;
      - code 0 et {"decision":"block","reason":...} sur stdout : bloquant, la
        raison est renvoyee a l'agent pour correction ;
      - autre code : erreur non bloquante.
    Le code 2 n'est pas employe : bloquant pour Claude Code, il n'est qu'un
    avertissement pour Copilot CLI.

    Messages sans accents : ils transitent par la console.
#>

Set-StrictMode -Version Latest

# --- 1. Payload -------------------------------------------------------------
# Un stdin absent ou illisible ne doit pas faire echouer le hook.
$payload = $null
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $payload = $raw | ConvertFrom-Json -ErrorAction Stop
    }
} catch {
    $payload = $null
}

function Get-PayloadField([string] $nom) {
    if ($payload -and $payload.PSObject.Properties.Name -contains $nom) {
        return $payload.$nom
    }
    return $null
}

# --- 2. Anti-boucle ----------------------------------------------------------
# Si ce hook a deja bloque la fin du tour en cours, ne pas rebloquer : l'agent a
# repris la main pour corriger, on le laisse aller au bout. Copilot CLI plafonne
# en outre a 8 blocages consecutifs.
if (Get-PayloadField 'stop_hook_active') { exit 0 }

# --- 3. Racine du projet -----------------------------------------------------
# Champ cwd du payload, fourni par les deux agents hotes ; a defaut,
# CLAUDE_PROJECT_DIR (Claude Code), puis le dossier courant.
$root = Get-PayloadField 'cwd'
if ([string]::IsNullOrWhiteSpace($root)) { $root = $env:CLAUDE_PROJECT_DIR }
if ([string]::IsNullOrWhiteSpace($root)) { $root = (Get-Location).Path }

$validateur = Join-Path $root 'scripts/validate.py'

# --- 4. Ne rien faire hors de ce depot --------------------------------------
# Le hook n'a de sens que la ou le validateur existe. Ailleurs : sortie neutre.
if (-not (Test-Path -LiteralPath $validateur -PathType Leaf)) { exit 0 }

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    [Console]::Error.WriteLine(
        "validate-tool : 'python' introuvable dans le PATH, validation ignoree.")
    exit 1  # non bloquant : c'est un defaut d'environnement, pas du travail produit
}

# --- 5. Lancer le validateur -------------------------------------------------
$sortie = & $python.Source $validateur 2>&1
$code = $LASTEXITCODE

if ($code -eq 0) { exit 0 }

# --- 6. Bloquer et remonter les ecarts --------------------------------------
$texte = ($sortie | Out-String).Trim()
$raison = @"
Le validateur du depot est rouge : le travail n'est pas termine.

$texte

Lire les ecarts ci-dessus, corriger, puis relancer :
    python scripts/validate.py
Ne pas contourner ce controle ni affaiblir la regle en cause.
"@

[Console]::Out.WriteLine(
    (@{ decision = 'block'; reason = $raison } | ConvertTo-Json -Compress))
exit 0
