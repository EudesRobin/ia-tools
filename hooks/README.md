# hooks

Hooks — scripts déclenchés par des événements de la session de l'agent hôte —
et leur configuration.

Enregistré dans la table de routage : [DOC_MAP.md](../docs/DOC_MAP.md).

## Hooks de ce dépôt

| Hook | Portée |
|---|---|
| [`validate-tool`](./validate-tool/HOOK.md) | **Local au dépôt.** Lance `scripts/validate.py` en fin de tour et empêche l'agent de rendre la main tant que le validateur est au rouge. |

`validate-tool` est enregistré dans deux fichiers versionnés du dépôt, un par
agent hôte : `.claude/settings.json` pour Claude Code et
`.github/hooks/validate-tool.json` pour Copilot CLI. Il **n'est pas distribué**
vers `{AGENT_DIR}` et ne demande aucune installation : il s'active à
l'ouverture d'une session dans ce dépôt. La procédure de
[SETUP.md](../docs/SETUP.md) §5 ne s'applique donc pas à lui.

## Ajouter un hook distribué

Un hook destiné à `{AGENT_DIR}` se compose de deux parties : un **script** et
son `HOOK.md`, dans un sous-dossier de `hooks/`, et un **enregistrement**
propre à chaque agent hôte — clé `hooks` de `~/.claude/settings.json` pour
Claude Code, fichier `~/.copilot/hooks/<nom>.json` pour Copilot CLI. **Ne jamais
écraser `{AGENT_DIR}/settings.json` en bloc** : n'y fusionner que les entrées de
hook concernées. Pour Copilot CLI, ce fichier propre au hook laisse
`~/.copilot/settings.json` intact.

Structure du `HOOK.md`, comportement du script et contrat commun aux deux
agents hôtes : [docs/CONVENTIONS.md](../docs/CONVENTIONS.md) §3. Installation
et précautions relatives à `settings.json` : [SETUP.md](../docs/SETUP.md) §5.
