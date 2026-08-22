# Sources and curation policy

## Included

| Source | Included |
| --- | ---: |
| JetBrains verified skills collection | 129 |
| Explicit local skills under `.agents/skills` | 15 |
| **Total** | **144** |

The JetBrains source is `https://github.com/JetBrains/skills`. Its README says
that every skill is a top-level directory and that each `SKILL.md` carries an
upstream source link. The local collection is represented by the existing
`sources/local-skills-lock.json` plus the locally adapted `impeccable` skill.

The captured JetBrains README and the local source lock are retained under
`sources/` for offline provenance review.

## Excluded

- KnowledgeGATE/Craft skills under `/home/omanand/Workspace/craft/**/skills`.
- Runtime-managed Codex plugin caches and bundled system skills.
- IDE and vendor extension skill directories from `.cursor`, `.gemini`, and
  `.vscode`.
- Dependencies, generated files, credentials, and machine-specific settings.

The exclusions prevent company-specific instructions, transient vendor caches,
and unrelated machine configuration from entering this reusable collection.
