# Status line — `usage-session`

Cette status line affiche en permanence dans Claude Code le modèle actif, le
niveau d'effort et le remplissage du contexte, puis les quotas de l'abonnement
ou, en facturation API, le coût estimé de la session. Le script ne lit que le
payload JSON que Claude Code lui transmet sur son entrée standard à chaque
rafraîchissement : il ne fait aucun appel au modèle et ne consomme aucun token.

## Ce qu'elle affiche

Abonnement Pro ou Max :

```text
Opus (high) │ ctx(42%) - (84k/200k) │ quota 5h (23%) │ quota 7j (41%)
```

Facturation API :

```text
Opus (high) │ ctx(42%) - (84k/200k) │ session ($1.23)
```

| Segment | Champ du payload | Règle |
|---|---|---|
| Modèle | `model.display_name` | à défaut, `model.id` |
| Effort | `effort.level` | omis si le modèle ne prend pas en charge le niveau d'effort |
| Contexte | `context_window.used_percentage`, `current_usage`, `context_window_size` | tokens = entrée + création de cache + lecture de cache, même formule que `used_percentage` ; `0` avant la première réponse |
| Quotas | `rate_limits.five_hour`, `rate_limits.seven_day` | affichés si l'un des deux est présent ; une fenêtre absente est omise |
| Coût | `cost.total_cost_usd` | affiché seulement sans quota et pour un montant non nul |

Les pourcentages sont colorés : vert sous 50 %, jaune à partir de 50 %, rouge à
partir de 80 %.

La ligne est alignée à droite : le script la fait précéder d'autant d'espaces
que le permet la largeur du terminal, que Claude Code lui transmet dans la
variable d'environnement `COLUMNS`. Sans cette variable, ou si la ligne ne tient
pas, elle reste alignée à gauche. Claude Code supprime les blancs en tête de
ligne : une séquence ANSI de réinitialisation, invisible, précède donc ces
espaces pour qu'ils soient conservés.

### Ce qu'elle ne fait délibérément pas

- **Elle n'écrit aucun fichier.** Le script est sans état : aucun cumul entre
  sessions, aucune estimation mensuelle.
- **Elle n'échoue jamais.** Sur un payload absent, illisible ou incomplet, le
  script produit un affichage réduit — au minimum le modèle s'il est connu,
  sinon rien — et se termine avec le code 0, sans rien écrire sur la sortie
  d'erreur.
- **Elle n'affiche pas l'heure de réinitialisation** des quotas.

## Installation

Une status line s'installe en deux temps : la copie du script sous
`~/.claude/statuslines/usage-session/`, puis l'enregistrement de la clé
`statusLine` dans `~/.claude/settings.json`. La procédure est décrite dans
`docs/SETUP.md` du dépôt ia-tools. `scripts/install.py` copie `statusline.ps1`
et affiche l'état de la clé, sans jamais écrire `settings.json`.
**Ne jamais écraser `~/.claude/settings.json` en bloc** : n'y fusionner que la
clé `statusLine`, après accord de l'utilisateur quand la clé existante désigne
un autre script.

```json
{
  "statusLine": {
    "type": "command",
    "command": "pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"<AGENT_DIR absolu, barres obliques>/statuslines/usage-session/statusline.ps1\""
  }
}
```

- Le chemin s'écrit avec des barres obliques `/` : Claude Code exécute la
  commande par Git Bash lorsque celui-ci est installé, et Git Bash traite la
  barre oblique inverse comme un caractère d'échappement.
- `pwsh` peut être remplacé par `powershell` (PowerShell 5.1, intégré à
  Windows).
- `-ExecutionPolicy Bypass` est nécessaire sous PowerShell 5.1, dont la
  stratégie d'exécution par défaut refuse les scripts. Ce paramètre ne
  s'applique qu'au processus lancé par la commande.

La status line apparaît au rafraîchissement suivant, sans redémarrage.

## Configuration

Paramètres en tête de `statusline.ps1` :

| Paramètre | Défaut | Effet |
|---|---|---|
| `$Couleurs` | `$true` | couleurs ANSI ; désactivées aussi quand la variable d'environnement `NO_COLOR` existe |
| `$SeuilJaune` | `50` | pourcentage à partir duquel la valeur passe en jaune |
| `$SeuilRouge` | `80` | pourcentage à partir duquel la valeur passe en rouge |
| `$Separateur` | ` │ ` | séparateur entre segments |
| `$Alignement` | `'droite'` | `'droite'` complète la ligne par des espaces à gauche ; `'gauche'` n'ajoute rien |
| `$MargeDroite` | `7` | colonnes laissées libres à droite : les 6 que Claude Code réserve, plus 1 de marge |
| `$TailleContexteDefaut` | `200000` | taille de la fenêtre de contexte retenue quand le payload ne la fournit pas |

## Limites

- **Claude Code seul.** Copilot CLI dispose de ses propres options intégrées
  (`/statusline`) ; cette status line ne lui est pas destinée.
- **Le coût est une estimation** calculée par Claude Code au prix catalogue ; il
  peut différer de la facture et repart de zéro à chaque `/clear`.
- **Les quotas n'apparaissent qu'après la première réponse** de la session.
  Avant elle, un abonné ne voit ni quota ni coût.
- **L'alignement à droite dépend de la largeur réellement disponible.** Un
  champ `padding` dans la clé `statusLine`, ou l'espacement propre à Claude
  Code, réduit cette largeur : augmenter `$MargeDroite` si l'affichage est
  tronqué ou passe à la ligne. Après un redimensionnement du terminal,
  l'alignement n'est recalculé qu'au rafraîchissement suivant.
- **Une limite de dépense fixée par une passerelle** (`rate_limits.spend_limit`)
  n'est pas affichée : la session est alors traitée comme une session en
  facturation API.
- **`statusline.ps1` reste en ASCII.** PowerShell 5.1 lit un script sans BOM
  dans l'encodage ANSI : tout caractère non ASCII de `statusline.ps1` se
  construit donc par son code, comme le séparateur.
