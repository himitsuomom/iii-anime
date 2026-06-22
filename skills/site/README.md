# iii skills explorer

A zero-dependency static site for browsing and searching the top-level iii
skills. Ported from the `ai-engineering-from-scratch` curriculum site (command
palette + catalog + glossary) and adapted to iii's skill catalog.

## Pages

- **`index.html`** — the skill catalog, one card per `skills/iii-*`.
- **`glossary.html`** — core iii terms (worker, function, trigger, …) with live filtering.
- Press **⌘K / Ctrl+K** anywhere to open the command palette and search skills + glossary.

## How it works

The site is fully client-side: no fetch, no server, no build framework. All data
is generated into `data.js` from filesystem-truth:

```
skills/iii-*/SKILL.md
        │  python3 .github/scripts/build_skills_catalog.py
        ▼
skills/catalog.json   +   skills/site/glossary.json
        │  node skills/site/build.js
        ▼
skills/site/data.js   ->   window.SKILLS, window.GLOSSARY
```

## Develop

```bash
# 1. rebuild the catalog from the skill folders
python3 .github/scripts/build_skills_catalog.py

# 2. regenerate data.js from the catalog + glossary
node skills/site/build.js

# 3. serve the folder (any static server works)
python3 -m http.server -d skills/site 8080
```

`data.js` and `skills/catalog.json` are committed; CI (`skills-catalog.yml`)
fails if either drifts from the filesystem. After adding or editing a skill,
re-run steps 1–2 and commit the regenerated files.

To add a glossary term, edit `glossary.json` and re-run `node skills/site/build.js`.
