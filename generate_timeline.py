#!/usr/bin/env python3
"""Regenerate index.html's event data from timeline.csv.

The script only rewrites the `const EVENTS=[...]` line (and the two
"N händelser" placeholders in the header) inside index.html — all
markup, CSS and JS logic stay exactly as they are in the file today.
That means index.html continues to double as the template: edit its
styling/behavior directly, then re-run this script whenever
timeline.csv changes to refresh the data.

Usage:
    python3 generate_timeline.py
    python3 generate_timeline.py --csv timeline.csv --html index.html
    python3 generate_timeline.py --out preview.html   # write elsewhere, don't overwrite index.html
"""
import argparse
import json
import re
import sys
from pathlib import Path

# timeline.csv uses fine-grained, free-text categories (who sent a chat to
# whom, "Besökt hemsida" vs "Besökta hemsidor", etc). index.html's design
# only knows the 8 categories defined in CAT_COLOR/CAT_INDENT, so raw CSV
# categories are folded into those before rendering. Extend this map when
# new fine-grained labels show up in the CSV (the script will also warn
# about anything it doesn't recognize).
CATEGORY_MAP = {
    "SMS": "Chatt/SMS/Mejl",
    "Mejl Den tilltalade till Rådgivaren (S&P)": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till Målsäganden": "Chatt/SMS/Mejl",
    "Chatt Målsäganden till Den tilltalade": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till NN1": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till NN2": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till NN3": "Chatt/SMS/Mejl",
    "Chatt NN3 till Den tilltalade": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till NN4": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till NN5": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till en vän i USA": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till en gruppchatt": "Chatt/SMS/Mejl",
    "Chatt Den tilltalade till hennes mamma": "Chatt/SMS/Mejl",
    "Besökt hemsida": "Besökta hemsidor",
    "Citat ur Merck Manual Home Edition (MSD Manuals)": "Besökta hemsidor",
    "Inköp D-vitamin": "Inköp",
    "Inköp Kalium": "Inköp",
    "Förhör/värde": "Värde",
    # "Journal" is unambiguous in Swedish (medical record) but Google
    # Translate renders it as "magazine" in Chinese. "Patientjournal" is
    # the standard Swedish legal/medical term and translates correctly.
    "Journal": "Patientjournal",
}

# The published timeline strips the leading quote-wrapper CSV puts around a
# direct quote (e.g. `"Foo bar".` -> `Foo bar.`), but only the FIRST
# quoted clause — any later quoted phrases in the same description are
# left alone. This mirrors that exactly (verified byte-for-byte against
# the existing index.html content).
_LEADING_QUOTE_RE = re.compile(r'^"([^"]*)"')


def normalize_desc(desc: str) -> str:
    return _LEADING_QUOTE_RE.sub(r"\1", desc, count=1)


def parse_csv(csv_path: Path):
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    start = 0
    if lines and lines[0].split("|", 1)[0].strip().lower() == "datum":
        start = 1  # skip the "Datum|Kategori|Beskrivning" header row

    events = []
    for lineno, line in enumerate(lines[start:], start=start + 1):
        if not line.strip():
            continue  # blank lines are just visual spacing in the CSV
        parts = line.split("|", 2)
        if len(parts) != 3:
            print(f"WARNING: line {lineno} does not have 3 '|'-separated fields, skipping: {line!r}",
                  file=sys.stderr)
            continue
        date, cat, desc = (p.strip() for p in parts)
        if not date or not cat:
            print(f"WARNING: line {lineno} missing date/category, skipping: {line!r}", file=sys.stderr)
            continue
        events.append({"date": date, "cat": cat, "desc": desc})
    return events


def html_escape(text: str) -> str:
    # matches the escaping convention already used inside index.html's EVENTS array
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def known_categories(html_text: str):
    m = re.search(r"const CAT_COLOR=\{(.*?)\};", html_text, re.S)
    if not m:
        return set()
    return set(re.findall(r"'([^']+)':", m.group(1)))


def inject(html_text: str, events: list) -> str:
    # matches index.html's existing formatting: ", " inside each object,
    # but a bare "," (no space) between objects in the array
    events_json = "[" + ",".join(json.dumps(e, ensure_ascii=False) for e in events) + "]"

    new_text, n = re.subn(
        r"const EVENTS=\[.*?\];",
        lambda m: f"const EVENTS={events_json};",
        html_text, count=1, flags=re.S,
    )
    if n == 0:
        raise SystemExit("ERROR: could not find 'const EVENTS=[...]' in the HTML template.")

    count = len(events)
    new_text = re.sub(
        r'(<span class="big" id="cnt-big">)\d+(</span>)',
        lambda m: f"{m.group(1)}{count}{m.group(2)}",
        new_text,
    )
    new_text = re.sub(
        r'(<span id="cnt-label">)\d+( händelser</span>)',
        lambda m: f"{m.group(1)}{count}{m.group(2)}",
        new_text,
    )
    return new_text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default="timeline.csv", type=Path)
    parser.add_argument("--html", default="index.html", type=Path, help="template to read AND (by default) overwrite")
    parser.add_argument("--out", type=Path, help="write to this path instead of overwriting --html")
    args = parser.parse_args()

    html_text = args.html.read_text(encoding="utf-8")
    known = known_categories(html_text)

    raw_events = parse_csv(args.csv)
    if not raw_events:
        raise SystemExit("ERROR: no events parsed from CSV.")

    mapped_events = []
    for e in raw_events:
        cat = CATEGORY_MAP.get(e["cat"], e["cat"])
        mapped_events.append({"date": e["date"], "cat": cat, "desc": normalize_desc(e["desc"])})

    unknown = sorted({e["cat"] for e in mapped_events} - known)
    if unknown:
        print(f"WARNING: these categories are not defined in CAT_COLOR/CAT_INDENT in {args.html} "
              "and will silently fall back to Övrigt's color/gray until you add them (or add a "
              "CATEGORY_MAP entry in this script if it's just a new spelling of an existing category):",
              file=sys.stderr)
        for cat in unknown:
            print(f"  - {cat}", file=sys.stderr)

    events = [{"date": e["date"], "cat": html_escape(e["cat"]), "desc": html_escape(e["desc"])}
              for e in mapped_events]
    new_html = inject(html_text, events)

    out_path = args.out or args.html
    out_path.write_text(new_html, encoding="utf-8")
    print(f"Wrote {len(events)} events to {out_path}")


if __name__ == "__main__":
    main()
