# Conventions par défaut

Conventions appliquées sur tout point que ni le projet ni les instructions
globales de la session ne règlent. Toute règle du projet ou des instructions
globales les remplace, point par point.

## Message de commit

- Rédigé en français, concis et factuel.
- **50 mots au plus** pour le message entier, sujet et corps compris.
- Le sujet commence par un préfixe de classification suivi de `: `, pris dans
  cette liste et aucune autre :

  | Préfixe | Emploi |
  |---|---|
  | `feat` | nouvelle capacité |
  | `fix` | correction de comportement |
  | `chore` | entretien |
  | `docs` | documentation seule |
  | `refactor` | restructuration sans changement de comportement |
  | `test` | vérifications |
  | `build` | outillage ou installation |
  | `revert` | annulation d'un commit |

- Sujet à l'impératif ou nominal, sans point final.
- Corps facultatif, réservé au « pourquoi » que le sujet ne porte pas ; jamais
  une paraphrase du diff.
- Aucune attribution d'outil d'IA : ni `Co-Authored-By` désignant un agent, ni
  « Generated with », ni équivalent.

Exemples conformes :

```text
feat: skill pull-request (commit, branche et PR GitHub)
fix: sortie en code 1 quand un conflit subsiste
docs: « template » remplace « gabarit »
```

## Branche de travail

`<préfixe>/<sujet-en-kebab-case>`, le préfixe étant celui du commit principal :
`feat/skill-pull-request`, `docs/regle-settings-json`.

## Pull request

- Le titre suit les règles du sujet de commit.
- La description suit le template du projet, à défaut
  [template-pr.md](template-pr.md).
- Aucune attribution d'outil d'IA dans la description.
