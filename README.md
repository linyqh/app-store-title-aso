# app-store-title-aso

An agent skill for the App Store "title band": the app **name**, **subtitle**, and hidden **keyword field**, written per locale and backed by Apple's own public search data instead of guesswork.

Apple ranks search on the text in those three fields (plus category and user behavior). The description, promotional text, and screenshot captions are not stated ranking inputs, so this skill spends its effort where ranking actually happens, then validates every field against App Store limits and review rules before you paste it into App Store Connect.

## What's inside

| File | Purpose |
|------|---------|
| `SKILL.md` | The workflow: collect app facts, build a per-market candidate pool, cut by intent and winnability, assign name/subtitle/keyword slots, stack extra locales, validate, deliver with evidence labels |
| `scripts/asoscan.py` | Free research + validation CLI (Python standard library only) |
| `examples/metadata.example.json` | Input shape for `check`, from a real shipped listing |

## Install

```bash
git clone https://github.com/linyqh/app-store-title-aso ~/.agents/skills/app-store-title-aso
```

(Claude Code: `~/.claude/skills/`. Other agents: wherever they load `SKILL.md` skills from.)

Then ask your agent something like: "Use app-store-title-aso to write the name, subtitle and keywords for my app in English and Japanese for the US and Japan stores."

## Use the script alone

```bash
# Demand evidence: App Store search-box suggestions (optionally a–z expanded)
python3 scripts/asoscan.py suggest "virtual pet" "ai pet" --country us --expand
python3 scripts/asoscan.py suggest 電子寵物 --country tw

# Competition evidence: who ranks, how many put the term in their title, rating counts
python3 scripts/asoscan.py serp "ai companion" --country us

# Is a live app already using this exact name?
python3 scripts/asoscan.py names "Chonkfish: AI Pet Companion" --country us jp tw

# Validate limits, separators, cross-field repeats (incl. CJK), banned words, trademarks
python3 scripts/asoscan.py check examples/metadata.example.json
```

`check` exits non-zero on any error, so it also works in CI.

## Limits of the free data

- Autosuggest order and competitor titles are real signals, but there is **no search volume**. For popularity scores, plug in Apple Ads, Astro, Appeeky or similar; `SKILL.md` has thresholds for that case.
- The endpoints are public but undocumented by Apple and may change.
- `names` cannot see names reserved in App Store Connect but not yet released. Always keep a backup name.
- Cross-locale indexing (e.g. the US store also indexing Spanish (Mexico) and Chinese metadata) is industry-reported, not Apple-documented. The skill shows how to verify it with `suggest` before relying on it.

## License

MIT
