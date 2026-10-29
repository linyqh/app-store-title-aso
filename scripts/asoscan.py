#!/usr/bin/env python3
"""App Store title-band research and validation using Apple's free public endpoints.

Subcommands:
  suggest  Search-box autosuggest for seed terms (demand evidence).
  serp     Top apps for a term (competition evidence).
  names    Look for live apps already using a proposed name.
  check    Validate name / subtitle / keywords JSON against App Store rules.

Standard library only. Public endpoints are unofficial and rate limited;
results are evidence, not search volume.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import re
import statistics
import string
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

STOREFRONTS = {
    "us": 143441, "gb": 143444, "ca": 143455, "au": 143460, "nz": 143461,
    "jp": 143462, "kr": 143466, "cn": 143465, "tw": 143470, "hk": 143463,
    "sg": 143464, "my": 143473, "th": 143475, "vn": 143471, "id": 143476,
    "ph": 143474, "in": 143467, "de": 143443, "fr": 143442, "es": 143454,
    "it": 143450, "nl": 143452, "br": 143503, "mx": 143468, "ru": 143469,
    "sa": 143479, "ae": 143481, "tr": 143480,
}
UA = "AppStore/3.0 iOS/18.0 model/iPhone17,1"
LIMITS = {"name": 30, "subtitle": 30, "keywords": 100}
BANNED = {
    "free", "best", "top", "#1", "no.1", "number one", "leading", "app", "apps",
    "免费", "最好", "最佳", "第一", "推荐", "排名", "应用", "软件", "免費", "最強", "無料", "おすすめ", "ランキング",
    "무료", "최고",
}
APPLE_MARKS = ["iphone", "ipad", "apple watch", "apple", "ios", "macos", "siri", "airpods", "app store", "facetime", "imessage"]
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def storefront(country: str) -> int:
    try:
        return STOREFRONTS[country.lower()]
    except KeyError:
        sys.exit(f"unknown country '{country}'; known: {', '.join(sorted(STOREFRONTS))}")


def hints(term: str, country: str) -> list[str]:
    url = (
        "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
        f"?clientApplication=Software&term={urllib.parse.quote(term)}"
    )
    data = plistlib.loads(fetch(url, {"X-Apple-Store-Front": f"{storefront(country)},29"}))
    return [h["term"] for h in data.get("hints", []) if h.get("term")]


def search(term: str, country: str, limit: int) -> list[dict]:
    url = (
        "https://itunes.apple.com/search?entity=software"
        f"&term={urllib.parse.quote(term)}&country={country.lower()}&limit={limit}"
    )
    return json.loads(fetch(url))["results"]


def norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


def contains_term(title: str, term: str) -> bool:
    t, q = norm(title), norm(term)
    if CJK.search(q):
        return q in t
    return all(re.search(rf"\b{re.escape(w)}", t) for w in q.split())


# ---------------------------------------------------------------- suggest
def cmd_suggest(args: argparse.Namespace) -> None:
    out: dict[str, dict[str, list[str]]] = {}
    for country in args.country:
        out[country] = {}
        for term in args.terms:
            probes = [term]
            if args.expand and not CJK.search(term):
                probes += [f"{term} {c}" for c in string.ascii_lowercase]
            seen: list[str] = []
            for probe in probes:
                for h in hints(probe, country):
                    if h not in seen:
                        seen.append(h)
                if args.expand:
                    time.sleep(0.25)
            out[country][term] = seen
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    for country, terms in out.items():
        for term, found in terms.items():
            exact = next((i for i, h in enumerate(found) if norm(h) == norm(term)), None)
            pos = "absent" if exact is None else f"#{exact + 1}"
            print(f"[{country}] {term!r}: exact-term suggestion {pos}; {len(found)} suggestions")
            for i, h in enumerate(found[: args.show], 1):
                print(f"   {i:>2}. {h}")


# ---------------------------------------------------------------- serp
def cmd_serp(args: argparse.Namespace) -> None:
    rows = []
    for country in args.country:
        for term in args.terms:
            results = search(term, country, args.limit)
            top10 = results[:10]
            ratings10 = [r.get("userRatingCount", 0) for r in top10]
            row = {
                "country": country,
                "term": term,
                "results": len(results),
                "titles_with_term_top10": sum(contains_term(r["trackName"], term) for r in top10),
                "titles_with_term_topN": sum(contains_term(r["trackName"], term) for r in results),
                "median_ratings_top10": int(statistics.median(ratings10)) if ratings10 else 0,
                "max_ratings_top10": max(ratings10, default=0),
                "top": [
                    {"rank": i, "name": r["trackName"], "ratings": r.get("userRatingCount", 0),
                     "genre": r.get("primaryGenreName"), "id": r["trackId"]}
                    for i, r in enumerate(results[: args.show], 1)
                ],
            }
            rows.append(row)
            time.sleep(0.3)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for row in rows:
        print(
            f"[{row['country']}] {row['term']!r}: {row['titles_with_term_top10']}/10 top titles contain it "
            f"({row['titles_with_term_topN']}/{row['results']} overall); top-10 ratings median "
            f"{row['median_ratings_top10']:,}, max {row['max_ratings_top10']:,}"
        )
        for app in row["top"]:
            print(f"   {app['rank']:>2}. {app['name']}  [{app['ratings']:,} ratings, {app['genre']}]")


# ---------------------------------------------------------------- names
def cmd_names(args: argparse.Namespace) -> None:
    any_clash = False
    for name in args.names:
        brand = re.split(r"\s*[:：\-–—|]\s*", name, maxsplit=1)[0]
        for country in args.country:
            live = search(name, country, 50)
            if brand != name:
                live += search(brand, country, 50)
            exact = {r["trackId"]: r for r in live if norm(r["trackName"]) == norm(name)}
            same_brand = sorted({
                r["trackName"] for r in live
                if brand != name and norm(r["trackName"]).startswith(norm(brand)) and r["trackId"] not in exact
            })
            for r in exact.values():
                any_clash = True
                print(f"[{country}] CLASH {name!r} is live as id {r['trackId']}")
            if not exact:
                print(f"[{country}] ok    no live app named {name!r}")
            if same_brand:
                print(f"[{country}] note  live titles starting with {brand!r}: {same_brand[:5]}")
            time.sleep(0.3)
    print("Reserved-but-unreleased names are invisible here; App Store Connect is the only authority.")
    sys.exit(1 if any_clash else 0)


# ---------------------------------------------------------------- check
def tokens(text: str) -> list[str]:
    t = norm(text)
    parts = re.split(r"[\s,，、:：;；\-–—|/&+·・()（）\[\]【】!！?？.。'\"“”]+", t)
    return [p for p in parts if p]


def stem(word: str) -> str:
    if CJK.search(word) or len(word) <= 3:
        return word
    for suffix in ("ies", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def overlaps(token: str, text: str) -> bool:
    if CJK.search(token):
        return token in norm(text).replace(" ", "")
    return stem(token) in {stem(w) for w in tokens(text)}


def shared_cjk(a: str, b: str, min_len: int = 2) -> list[str]:
    """Maximal CJK substrings (>= min_len) present in both texts."""
    a, b = norm(a).replace(" ", ""), norm(b).replace(" ", "")
    found: list[str] = []
    for i in range(len(a)):
        for j in range(len(a), i + min_len - 1, -1):
            piece = a[i:j]
            if len(piece) >= min_len and all(CJK.match(ch) for ch in piece) and piece in b:
                if not any(piece in f for f in found):
                    found.append(piece)
                break
    return found


def check_locale(locale: str, meta: dict, brands: list[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    name, subtitle, keywords = meta.get("name", ""), meta.get("subtitle", ""), meta.get("keywords", "")
    for field, value in (("name", name), ("subtitle", subtitle), ("keywords", keywords)):
        n = len(value)
        if n > LIMITS[field]:
            errors.append(f"{field} is {n}/{LIMITS[field]} characters")
    if keywords:
        if re.search(r"[,，]\s", keywords) or re.search(r"\s[,，]", keywords):
            errors.append("keywords: whitespace around a comma wastes characters")
        if "，" in keywords or "、" in keywords:
            errors.append("keywords: use ASCII ',' as the separator, not '，' or '、'")
        kws = [k.strip() for k in keywords.split(",")]
        if any(not k for k in kws):
            errors.append("keywords: empty entry (double or trailing comma)")
        seen: dict[str, str] = {}
        for k in filter(None, kws):
            key = stem(norm(k))
            if key in seen:
                errors.append(f"keywords: duplicate {k!r} (also {seen[key]!r})")
            seen[key] = k
            for field, text in (("name", name), ("subtitle", subtitle)):
                if overlaps(norm(k), text):
                    errors.append(f"keywords: {k!r} already indexed via {field}")
        used = len(keywords)
        if used < 90:
            warns.append(f"keywords use {used}/100 characters; fill the remaining budget")
    for t in tokens(subtitle):
        if not CJK.search(t) and overlaps(t, name) and len(t) > 1:
            warns.append(f"subtitle repeats {t!r} from name")
    for piece in shared_cjk(subtitle, name):
        warns.append(f"subtitle repeats {piece!r} from name")
    all_text = " ".join((name, subtitle, keywords))
    for word in BANNED:
        if CJK.search(word):
            if word in norm(all_text):
                warns.append(f"risky/banned word {word!r} (guideline 2.3.7; low search value)")
        elif re.search(rf"(?<![\w#]){re.escape(word)}(?!\w)", norm(all_text)):
            warns.append(f"risky/banned word {word!r} (guideline 2.3.7; low search value)")
    for mark in APPLE_MARKS:
        if re.search(rf"\b{re.escape(mark)}\b", norm(name + " " + subtitle)):
            errors.append(f"Apple trademark {mark!r} in name/subtitle (guideline 5.2.5)")
    for brand in brands:
        if brand and norm(brand) in norm(all_text):
            errors.append(f"third-party brand {brand!r} in metadata (guideline 2.3.7 / 5.2)")
    return errors, warns


def cmd_check(args: argparse.Namespace) -> None:
    spec = json.load(open(args.file, encoding="utf-8"))
    locales: dict[str, dict] = spec["locales"]
    brands: list[str] = spec.get("blocked_brands", [])
    failed = False
    for locale, meta in locales.items():
        errors, warns = check_locale(locale, meta, brands)
        counts = " ".join(f"{f}={len(meta.get(f, ''))}/{LIMITS[f]}" for f in LIMITS)
        status = "FAIL" if errors else "ok"
        print(f"{locale:<8} {status:<4} {counts}")
        for e in errors:
            print(f"   ERROR {e}")
        for w in warns:
            print(f"   warn  {w}")
        failed |= bool(errors)
    for group, members in spec.get("storefront_groups", {}).items():
        present = [m for m in members if m in locales]
        owner: dict[str, str] = {}
        for loc in present:
            meta = locales[loc]
            for t in tokens(" ".join((meta.get("name", ""), meta.get("subtitle", ""), meta.get("keywords", "")))):
                if len(t) < 2:
                    continue
                key = stem(t)
                if key in owner and owner[key] != loc:
                    print(f"[{group}] warn  {t!r} appears in both {owner[key]} and {loc}; spend one slot on a new term")
                owner.setdefault(key, loc)
    sys.exit(1 if failed else 0)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("suggest", help="search-box autosuggest (demand evidence)")
    s.add_argument("terms", nargs="+")
    s.add_argument("--country", nargs="+", default=["us"])
    s.add_argument("--expand", action="store_true", help="also probe '<term> a'..'<term> z' (Latin terms only)")
    s.add_argument("--show", type=int, default=10)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_suggest)

    r = sub.add_parser("serp", help="top apps for a term (competition evidence)")
    r.add_argument("terms", nargs="+")
    r.add_argument("--country", nargs="+", default=["us"])
    r.add_argument("--limit", type=int, default=25)
    r.add_argument("--show", type=int, default=10)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_serp)

    n = sub.add_parser("names", help="find live apps already using a proposed name")
    n.add_argument("names", nargs="+")
    n.add_argument("--country", nargs="+", default=["us"])
    n.set_defaults(func=cmd_names)

    c = sub.add_parser("check", help="validate a metadata JSON file")
    c.add_argument("file")
    c.set_defaults(func=cmd_check)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
