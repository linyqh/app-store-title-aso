---
name: app-store-title-aso
description: Research and write the App Store "title band" — app name, subtitle, and keyword field — per locale, backed by Apple's public search data, validated against App Store limits and review rules. Use when asked to name an app, write or optimize its title/subtitle/keywords, fix a name collision, localize ASO metadata, or for 标题/副标题/关键词/ASO/店铺名称/タイトル/サブタイトル/キーワード.
---

# App Store title band (name · subtitle · keywords)

RFC 2119 keywords apply. `NEVER` = MUST NOT; `AVOID` = SHOULD NOT.

Apple ranks search on text relevance of **name, subtitle, keyword field, primary category**, plus user behavior (downloads, ratings, conversion) — [App Store search](https://developer.apple.com/app-store/search/). Description, promotional text, and screenshot text do not feed ranking as far as Apple has ever stated. The title band is therefore the whole keyword game; everything else is conversion.

<critical>
- Name 30, subtitle 30, keyword field 100 characters, per locale. Over by one = rejected save.
- A word already in name or subtitle is wasted in the keyword field. Apple combines words across the three fields.
- NEVER put competitor names, other brands, Apple product names (name/subtitle), prices, "free", "best", "#1" in the title band (guidelines 2.3.7, 5.2.5).
- Every claim in the deliverable carries an evidence label; NEVER present a guess as data.
- Name, subtitle, keywords change only with a new version submission. Promotional text is the only live-editable field and is not indexed.
</critical>

Script: `python3 <skill-dir>/scripts/asoscan.py <suggest|serp|names|check> …` (stdlib only; `--help` per subcommand). Data comes from Apple's public autosuggest and iTunes Search endpoints: real, free, unofficial, no search volume.

## 1. Collect inputs

Ask once, in one message, only for what the repo/listing cannot answer:

- What the app does, for whom, and the 1–2 things competitors do not do.
- Brand name and the home-screen display name (`CFBundleDisplayName`).
- Target storefronts (e.g. us, jp, tw) and the locales you will fill.
- Live or unreleased. Live → read current name/subtitle/keywords first (App Store Connect, `asc`, or `fastlane deliver download_metadata`).
- Words to avoid: trademarks, competitor brands, review-risk words for the category (e.g. "girlfriend/恋爱/女友" for AI companions rated 13+).

## 2. Build the candidate pool per market

- Seed from the app's concepts, category vocabulary, and competitor titles/subtitles. Research **what each market types**, not a translation of English terms (`ペット育成`, not a literal "virtual pet" calque).
- Expand with autosuggest; order of suggestions is the only free demand signal:
  ```bash
  asoscan.py suggest "virtual pet" "ai pet" --country us --expand
  asoscan.py suggest 電子寵物 --country tw
  ```
  An exact-term suggestion near the top = people type it. Absent on every storefront = treat demand as unknown-low (e.g. `桌宠` returned nothing on us/tw/sg).
- Measure competition for survivors:
  ```bash
  asoscan.py serp "virtual pet" "ai companion" --country us
  ```
  Read: how many top-10 titles carry the term (devs converge on terms that get searched), and the top-10 median rating count (authority you must beat).

## 3. Cut by intent and winnability

For each candidate decide, in one line each:

- **Intent**: would someone typing this want this app? Too generic ("tracker", "AI") or adjacent-but-wrong ("pet care" for a virtual pet) → cut, however popular.
- **Demand**: suggested as an exact term? Seen in competitor titles? Neither → long-tail filler only, never the name slot.
- **Winnability**: top-10 median ratings far above what the app will have in 3 months → long-term bet; it MAY go in the name if it is the defining category word, but the keyword field MUST carry winnable terms for now.

With paid data (Apple Ads popularity, Astro, Appeeky), use these gates instead of judgment: name pop ≥ 40 or rank ≤ 5; subtitle pop ≥ 30 or rank ≤ 10; keyword field pop ≥ 20 or rank ≤ 20; drop pop ≤ 10. A popularity at the tool's floor (e.g. 5) means "unmeasured", not zero.

## 4. Assign slots

| Slot | Gets | Shape |
|---|---|---|
| Name (30) | Brand + the strongest category term | `Brand: Category Term` — e.g. `Chonkfish: AI Pet Companion` |
| Subtitle (30) | Second keyword cluster inside the differentiating benefit | Benefit sentence, not slogan — `Chat buddy that remembers you` |
| Keyword field (100) | Remaining winnable terms, highest value first | `term,term,term` — no spaces, no repeats, ≥ 95 chars used |

Rules:

- Brand first when the home-screen name is the brand (store and device names stay recognizably the same). Descriptor first (`Calorie Tracker – Glow Up`) is valid for generic utilities; the "earlier = heavier" position effect is industry belief, not Apple-stated.
- A name collision ("already being used") is solved by brand + descriptor, which is also better ASO. Exact-name uniqueness is global; reserved-but-unreleased names are invisible to `names`.
- Subtitle MUST NOT repeat name words. Name 3–5 meaningful tokens max; more reads as stuffing and costs conversion.
- Keyword field: singular English forms (Apple matches plurals); split phrases into atoms Apple can recombine (`电子` + subtitle `宠物` → matches 电子宠物); skip words Apple infers (app, the category name, your brand).
- CJK: no spaces needed; ASCII commas only; tokenize by real search words, not single characters or long mashed runs.
- AVOID filling with words whose intent does not match just to reach 100 characters; prefer the next real term in another market's locale (step 5).

## 5. Cross-locale stacking (extra keyword budget)

A storefront indexes metadata from more than one locale. Industry-reported, not Apple-documented: the US storefront also indexes Spanish (Mexico), Chinese (Simplified/Traditional), and several others. Each extra indexed locale = another name/subtitle/100-char keyword field for that storefront.

- Verify before relying on it: on the target storefront, query a term that exists only in the secondary locale's script:
  ```bash
  asoscan.py suggest 电子宠物 --country us   # Chinese titles returned on US → zh is indexed there
  ```
- Fill the secondary locale with **different** terms from the primary; duplicates across stacked locales waste the slot. `check` warns on this when `storefront_groups` is set.
- The secondary locale's copy is still shown to its own-language users: keep it truthful and readable, even when it carries a second English keyword set (e.g. es-MX on a US-focused app).

## 6. Validate

Write a JSON file (shape: `examples/metadata.example.json`) and run:

```bash
asoscan.py check metadata.json          # limits, separators, repeats, banned words, trademarks, stacking overlap
asoscan.py names "Chonkfish: AI Pet Companion" --country us jp tw
```

`check` exits non-zero on any ERROR; fix every ERROR, decide on each warn. App Store Connect save is the final authority for name availability: always ship 1–2 backup names that keep the brand and swap the descriptor.

## 7. Deliver

Per locale, a paste-ready block:

```
## en-US  (storefronts: us)
Name      Chonkfish: AI Pet Companion        27/30
Subtitle  Chat buddy that remembers you      29/30
Keywords  virtual,friend,chatbot,…           95/100
Backup    Chonkfish: Virtual Pet Chat        27/30
```

Then:

1. **Coverage matrix** — each target term × {name, subtitle, keywords, stacked locale}.
2. **Evidence table** — term, slot, demand (`suggest #n` / absent), competition (`k/10 titles`, median ratings), label:
   - `[DATA]` from `asoscan.py` output or a paid tool, with the number;
   - `[JUDGMENT]` intent/positioning call;
   - `[INFERENCE]` unverified industry belief (stacking tables, position weight, OCR).
3. **Rejected terms** with one-line reasons (generic, wrong intent, trademark, review risk).
4. **Next checks**: re-measure rankings 2–4 weeks after the version ships; name/subtitle/keyword edits ride the next version.

## Pitfalls seen in practice

- Literal translation of English keywords into ja/zh — locals search other words; research per market.
- Spending the subtitle on a slogan ("Feel amazing every day") — zero search value.
- Treating screenshot captions as indexed keywords — Apple has never confirmed OCR ranking.
- Using the developer/brand of a model or service (e.g. an AI vendor name) in keywords — trademark rejection.
- Review-risk vocabulary for the age rating (romance/"girlfriend" terms on a companion app) — rejection plus 4+/13+ mismatch.
- Fixed one locale's collision and forgot the others — rerun `names` and `check` across every locale after any change.

<critical>
- Run `asoscan.py check` and fix all ERRORs before delivering.
- Label every recommendation `[DATA]`, `[JUDGMENT]`, or `[INFERENCE]`.
- No word twice across name, subtitle, and keyword field within a locale.
</critical>
