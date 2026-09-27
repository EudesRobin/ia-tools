#Requires -Version 7
<#
    Hook Stop — lance scripts/validate.py en fin de tour et empeche de rendre la
    main tant qu'il est rouge.

    Contrairement aux hooks distribues (voir docs/CONVENTIONS.md section 3.2),
    celui-ci bloque volontairement : c'est son objet meme. Il est enregistre
    localement au depot, jamais dans la configuration globale d'un agent hote.

    Contrat commun a Claude Code et a Copilot CLI (CONVENTIONS.md section 3.2) :
      - payload JSON sur stdin (cwd, session_id, stop_hook_active) ;
      - code 0 sans sortie : rien a signaler, le tour se termine ;
      - code 0 et {"decision":"block","reason":...} sur stdout : bloquant, la
        raison est renvoyee a l'agent pour correction ;
      - autre code : erreur non bloquante.
    Le code 2 n'est pas employe : bloquant pour Claude Code, il n'est qu'un
    avertissement pour Copilot CLI.

    Anti-boucle : au plus $MaxBlocages blocages consecutifs dans un tour, puis la
    main est rendue avec un avertissement. Le code 2 du validateur signale une
    anomalie d'environnement et ne bloque pas.

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

# --- 2. Parametres ----------------------------------------------------------
# Blocages consecutifs admis avant de rendre la main au rouge (anti-boucle).
# Copilot CLI plafonne de son cote a 8.
$MaxBlocages = 3

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

# Compteur de blocages consecutifs, propre a la session (a defaut, au depot).
$cle = Get-PayloadField 'session_id'
if ([string]::IsNullOrWhiteSpace($cle)) { $cle = Get-PayloadField 'sessionId' }
if ([string]::IsNullOrWhiteSpace($cle)) { $cle = $root }
$hash = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($cle))).Substring(0, 16)
$compteur = Join-Path ([IO.Path]::GetTempPath()) "validate-tool-$hash.count"

# Premier arret du tour (stop_hook_active faux ou absent) : le compteur repart de
# zero, pour qu'un tour interrompu n'entame pas le quota du suivant.
if (-not (Get-PayloadField 'stop_hook_active')) {
    Remove-Item -LiteralPath $compteur -ErrorAction SilentlyContinue
}

# --- 5. Lancer le validateur -------------------------------------------------
$sortie = & $python.Source $validateur 2>&1
$code = $LASTEXITCODE

if ($code -eq 0) {
    Remove-Item -LiteralPath $compteur -ErrorAction SilentlyContinue
    exit 0
}
if ($code -eq 2) {
    # Anomalie d'environnement signalee par le validateur : pas du travail produit.
    [Console]::Error.WriteLine("validate-tool : " + ($sortie | Out-String).Trim())
    exit 1
}

$n = 0
if (Test-Path -LiteralPath $compteur) { $n = [int](Get-Content -LiteralPath $compteur -Raw) }
if ($n -ge $MaxBlocages) {
    Remove-Item -LiteralPath $compteur -ErrorAction SilentlyContinue
    [Console]::Error.WriteLine(
        "validate-tool : validateur toujours rouge apres $MaxBlocages blocages, main rendue.")
    exit 1
}
Set-Content -LiteralPath $compteur -Value ($n + 1) -NoNewline

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
