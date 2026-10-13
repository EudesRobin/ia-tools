# hooks

Hooks — scripts déclenchés par des événements de la session de l'agent hôte —
et leur configuration.

Enregistré dans la table de routage : [DOC_MAP.md](../docs/DOC_MAP.md).

## Hooks de ce dépôt

| Hook | Portée |
|---|---|
| [`validate-tool`](./validate-tool/HOOK.md) | **Local au dépôt.** Lance `scripts/validate.py` en fin de tour et empêche l'agent de rendre la main tant que le validateur est en échec. |

`validate-tool` est enregistré dans deux fichiers versionnés du dépôt, un par
agent hôte : `.claude/settings.json` pour Claude Code et
`.github/hooks/validate-tool.json` pour Copilot CLI. Il **n'est pas distribué**
vers `{AGENT_DIR}` et ne demande aucune installation : il s'active à
l'ouverture d'une session dans ce dépôt. La procédure de
[SETUP.md](../docs/SETUP.md) §5 ne s'applique donc pas à lui.

## Ajouter un hook distribué

Un hook destiné à `{AGENT_DIR}` se compose de deux parties : d'une part un
**script** et son `HOOK.md`, dans un sous-dossier de `hooks/`, d'autre part un
**enregistrement** propre à chaque agent hôte — clé `hooks` du fichier de
paramètres `~/.claude/settings.json` pour Claude Code, fichier d'enregistrement
dédié `~/.copilot/hooks/<nom>.json` pour Copilot CLI. **Ne jamais écraser
`~/.claude/settings.json` en bloc** : n'y merger que les entrées de hook
concernées. Copilot CLI admet aussi une clé `hooks` dans son fichier de
paramètres `~/.copilot/settings.json` ; le fichier d'enregistrement dédié laisse
ce fichier intact. Un fichier d'enregistrement déjà présent n'est pas écrasé non
plus : n'y merger que les entrées de hook concernées.

Structure du `HOOK.md`, comportement du script et contrat commun aux deux agents
hôtes : [docs/CONVENTIONS.md](../docs/CONVENTIONS.md) §3. Installation et
précautions relatives aux fichiers de paramètres et d'enregistrement :
[SETUP.md](../docs/SETUP.md) §5.
