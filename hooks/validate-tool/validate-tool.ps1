#Requires -Version 7
<#
    Hook Stop — lance scripts/validate.py en fin de tour et empeche de rendre la
    main tant qu'il est rouge.

    Contrairement aux hooks distribues (voir docs/CONVENTIONS.md section 3.2),
    celui-ci sort volontairement en code bloquant : c'est son objet meme. Il est
    enregistre localement au depot, jamais dans ~/.claude/settings.json.

    Contrat Claude Code :
      - charge utile JSON sur stdin (dont stop_hook_active) ;
      - code 0  : rien a signaler, le tour se termine ;
      - code 2  : bloquant, stderr est renvoye a Claude pour correction ;
      - autre   : erreur non bloquante, stderr affiche a l'utilisateur.

    Messages sans accents : ils transitent par la console.
#>

Set-StrictMode -Version Latest

# --- 1. Charge utile ---------------------------------------------------------
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

# --- 2. Anti-boucle ----------------------------------------------------------
# Si ce hook a deja bloque la fin du tour en cours, ne pas rebloquer : Claude a
# repris la main pour corriger, on le laisse aller au bout.
if ($payload -and $payload.PSObject.Properties.Name -contains 'stop_hook_active') {
    if ($payload.stop_hook_active) { exit 0 }
}

# --- 3. Racine du projet -----------------------------------------------------
# CLAUDE_PROJECT_DIR est fourni par Claude Code ; repli sur le dossier courant.
$root = $env:CLAUDE_PROJECT_DIR
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
[Console]::Error.WriteLine(@"
Le validateur du depot est rouge : le travail n'est pas termine.

$texte

Lire les ecarts ci-dessus, corriger, puis relancer :
    python scripts/validate.py
Ne pas contourner ce controle ni affaiblir la regle en cause.
"@)
exit 2
