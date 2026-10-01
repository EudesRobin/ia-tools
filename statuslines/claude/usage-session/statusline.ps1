<#
    Status line usage-session - modele, effort, contexte, puis quotas
    (abonnement) ou cout de la session (facturation API).

    Contrat de Claude Code :
      - payload JSON sur stdin, a chaque rafraichissement ;
      - la premiere ligne ecrite sur stdout est affichee ;
      - aucun appel au modele : rien n'est consomme en tokens.

    Le script n'echoue jamais : toute erreur produit un affichage minimal et le
    code 0. Il n'ecrit aucun fichier.

    Compatible PowerShell 5.1 et 7. Le fichier reste en ASCII : PowerShell 5.1
    lit un script sans BOM dans l'encodage ANSI, ce qui corromprait tout
    caractere non ASCII. Les symboles sont donc construits par leur code.
#>

# --- 1. Parametres ----------------------------------------------------------
# Couleurs ANSI par seuil ; desactivees aussi si la variable NO_COLOR existe.
$Couleurs = $true
# Seuils en pourcentage : vert en dessous de $SeuilJaune, rouge a partir de $SeuilRouge.
$SeuilJaune = 50
$SeuilRouge = 80
# Separateur entre segments : trait vertical U+2502.
$Separateur = ' ' + [char]0x2502 + ' '
# Alignement : 'droite' complete la ligne par des espaces a gauche, d'apres la
# largeur du terminal que Claude Code fournit dans COLUMNS ; 'gauche' n'ajoute rien.
$Alignement = 'droite'
# Colonnes laissees libres a droite : Claude Code en reserve 6, plus 1 de marge.
$MargeDroite = 7
# Taille de la fenetre de contexte retenue quand le payload ne la fournit pas.
$TailleContexteDefaut = 200000

# --- 2. Outils ---------------------------------------------------------------
$Invariant = [Globalization.CultureInfo]::InvariantCulture
if ($env:NO_COLOR) { $Couleurs = $false }

function Get-Champ($objet, [string] $chemin) {
    # Acces tolerant : $null des qu'un maillon du chemin manque.
    foreach ($nom in $chemin.Split('.')) {
        if ($null -eq $objet) { return $null }
        $prop = $objet.PSObject.Properties[$nom]
        if ($null -eq $prop) { return $null }
        $objet = $prop.Value
    }
    return $objet
}

function Format-Pourcent($valeur) {
    $n = [int][math]::Round([double]$valeur)
    $texte = "$n%"
    if (-not $Couleurs) { return $texte }
    $code = '32'
    if ($n -ge $SeuilJaune) { $code = '33' }
    if ($n -ge $SeuilRouge) { $code = '31' }
    return [char]27 + "[${code}m" + $texte + [char]27 + '[0m'
}

function Format-Tokens($n) {
    $n = [double]$n
    if ($n -ge 1000000) { return ($n / 1000000).ToString('0.#', $Invariant) + 'M' }
    if ($n -ge 1000) { return ([math]::Round($n / 1000)).ToString($Invariant) + 'k' }
    return ([math]::Round($n)).ToString($Invariant)
}

function Get-Aligne([string] $texte) {
    # Largeur visible : sans les sequences ANSI de couleur.
    if ($Alignement -ne 'droite') { return $texte }
    $colonnes = 0
    if (-not [int]::TryParse("$env:COLUMNS", [ref]$colonnes)) { return $texte }
    $visible = ($texte -replace ([string][char]27 + '\[[0-9;]*m'), '').Length
    $vide = $colonnes - $visible - $MargeDroite
    if ($vide -le 0) { return $texte }
    # Claude Code supprime les blancs en tete de ligne : une sequence ANSI de
    # reinitialisation, invisible, les precede pour qu'ils soient conserves.
    return [char]27 + '[0m' + (' ' * $vide) + $texte
}

function Write-Sortie([string] $texte) {
    # Ecriture en octets UTF-8 : independante de l'encodage de la console.
    $octets = (New-Object System.Text.UTF8Encoding($false)).GetBytes($texte)
    $flux = [Console]::OpenStandardOutput()
    $flux.Write($octets, 0, $octets.Length)
    $flux.Flush()
}

# --- 3. Affichage ------------------------------------------------------------
$modele = $null
try {
    $lecteur = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
    $payload = $lecteur.ReadToEnd() | ConvertFrom-Json -ErrorAction Stop

    # Modele et effort : "Opus (high)".
    $modele = Get-Champ $payload 'model.display_name'
    if (-not $modele) { $modele = Get-Champ $payload 'model.id' }
    $tete = "$modele"
    $effort = Get-Champ $payload 'effort.level'
    if ($effort) { $tete += " ($effort)" }
    $segments = @($tete)

    # Contexte : "ctx(42%) - (84k/200k)". Les tokens suivent la formule de
    # used_percentage : entree + creation de cache + lecture de cache.
    $taille = Get-Champ $payload 'context_window.context_window_size'
    if ($null -eq $taille) { $taille = $TailleContexteDefaut }
    $pct = Get-Champ $payload 'context_window.used_percentage'
    $usage = Get-Champ $payload 'context_window.current_usage'
    $tokens = $null
    if ($null -ne $usage) {
        $tokens = 0
        foreach ($cle in 'input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens') {
            $v = Get-Champ $usage $cle
            if ($null -ne $v) { $tokens += [double]$v }
        }
    }
    if ($null -eq $tokens -and $null -ne $pct) { $tokens = [double]$pct * $taille / 100 }
    if ($null -eq $tokens) { $tokens = 0 }
    if ($null -eq $pct) { $pct = 100 * $tokens / $taille }
    $segments += 'ctx(' + (Format-Pourcent $pct) + ') - (' + (Format-Tokens $tokens) + '/' + (Format-Tokens $taille) + ')'

    # Quotas si l'abonnement en publie, sinon cout de la session s'il est connu.
    $cinq = Get-Champ $payload 'rate_limits.five_hour.used_percentage'
    $sept = Get-Champ $payload 'rate_limits.seven_day.used_percentage'
    if ($null -ne $cinq -or $null -ne $sept) {
        if ($null -ne $cinq) { $segments += 'quota 5h (' + (Format-Pourcent $cinq) + ')' }
        if ($null -ne $sept) { $segments += 'quota 7j (' + (Format-Pourcent $sept) + ')' }
    } else {
        $cout = Get-Champ $payload 'cost.total_cost_usd'
        if ($null -ne $cout -and [double]$cout -gt 0) {
            $segments += 'session ($' + ([double]$cout).ToString('0.00', $Invariant) + ')'
        }
    }

    Write-Sortie (Get-Aligne ($segments -join $Separateur))
} catch {
    try { Write-Sortie "$modele" } catch { }
}
exit 0
