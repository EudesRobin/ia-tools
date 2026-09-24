# hooks

Hooks Claude — scripts déclenchés par des événements de la session — et leur
configuration.

Enregistré dans la table de routage : [DOC_MAP.md](../docs/DOC_MAP.md).

## Hooks de ce dépôt

| Hook | Portée |
|---|---|
| [`validate-tool`](./validate-tool/HOOK.md) | **Local au dépôt.** Lance `scripts/validate.py` en fin de tour et empêche Claude de rendre la main tant qu'il est au rouge. |

`validate-tool` est enregistré dans le `.claude/settings.json` versionné du
dépôt et **n'est pas distribué** vers `~/.claude/` : rien à installer : il
s'active à l'ouverture d'une session dans ce dépôt. La procédure de
[SETUP.md](../docs/SETUP.md) §5 ne s'applique donc pas à lui.

## Ajouter un hook distribué

Un hook destiné à `~/.claude/` se compose de deux parties : un **script** et son
`HOOK.md`, dans un sous-dossier de `hooks/`, puis un **enregistrement** dans
`~/.claude/settings.json`, clé `hooks`.

Structure du `HOOK.md` et comportement du script :
[docs/CONVENTIONS.md](../docs/CONVENTIONS.md) §3. Installation et prudence sur
`settings.json` : [SETUP.md](../docs/SETUP.md) §5.
