#!/usr/bin/env python3
"""Source-of-truth gate (gate 6 of the Agency Hub automation plan, QUEST, 2 Oct 2026).

The site publishes https://orynquest.com/facts.json, generated from the code's
own constants on every release (plans, the cancellation schedule, the move
cutoff, Stripe payout rules, the assistant's name, the service area, the
vendor-cost wording). This checks that docs/parent-facts.md and
docs/vendor-facts.md still state each of those numbers and phrases, and prints
one line per drift. It never edits the sheets: a person (or the Hub, through a
pull request) fixes them.

  facts_drift.py [--url https://orynquest.com/facts.json | --file facts.json] [--out drift.md]

Exit 0 always. Writes `status=ok|drift|skipped` to $GITHUB_OUTPUT when set.
While /facts.json answers 404 (before the release that adds it) it skips with
a notice.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SHEETS = {"parent": Path("docs/parent-facts.md"), "vendor": Path("docs/vendor-facts.md")}
DASH = r"\s*(?:-|–|—|to|through)\s*"


def norm(text: str) -> str:
    text = text.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x00A0: " "})
    return re.sub(r"[ \t]+", " ", text)  # keep line breaks: each fact is checked within one line


def lines_with(text: str, word: str) -> list[str]:
    return [l for l in text.splitlines() if re.search(word, l, re.I)]


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def checks(facts: dict) -> list[tuple[str, str, callable]]:
    """(sheet, what the code says, test(sheet text) -> bool). Which sheet must
    state which fact is decided HERE: the parent sheet links to /pricing
    instead of quoting plan numbers, so it must carry the plan names and their
    one-line descriptions, not the credits or prices."""
    out = []
    for plan in facts["plans"]:
        out.append(("parent", f'plan "{plan["name"]}" with its description "{plan["description"]}"',
                    lambda t, p=plan: has(t, rf"\b{re.escape(p['name'])}\b") and norm(p["description"]).lower() in t.lower()))
    tiers = sorted(facts["cancellation"]["schedule"], key=lambda s: -s["moreThanHoursBefore"])
    hours = [t["moreThanHoursBefore"] for t in tiers if t["moreThanHoursBefore"] > 0]
    pcts = [t["refundPercent"] for t in tiers]
    sched = ", ".join(f">{t['moreThanHoursBefore']} h → {t['refundPercent']}%" for t in tiers)

    def cancel_ok(t: str) -> bool:
        for line in lines_with(t, r"cancel"):
            ok_h = all(has(line, rf"\b{h}\s*(?:hours?|h)\b|\b{h}{DASH}\d+\s*(?:hours?|h)\b|\d+{DASH}{h}\s*(?:hours?|h)\b") for h in hours)
            ok_p = all(has(line, rf"\b{p}%") if p > 0 else has(line, r"\b0%|nothing|no refund|none\b") for p in pcts)
            if ok_h and ok_p:
                return True
        return False

    def move_ok(t: str, h=facts["moves"]["cutoffHoursBeforeClass"]) -> bool:
        return any(has(l, rf"\b{h}\s*(?:hours?|h)\b|\b{h}-hour") for l in lines_with(t, r"\bmov(e|es|ed|ing)\b"))

    name = facts["assistant"]["name"]
    area = facts["serviceArea"]
    zips = rf"\b{area['zipPrefixFrom']}{DASH}{area['zipPrefixTo']}\b"
    pay = facts["vendorPayouts"]
    wording = norm(facts["vendorCost"]["wording"]).lower()
    for sheet in ("parent", "vendor"):
        out.append((sheet, f"cancellation schedule {sched}", cancel_ok))
        out.append((sheet, f"moves close {facts['moves']['cutoffHoursBeforeClass']} hours before class", move_ok))
        out.append((sheet, f'the assistant is "{name}"', lambda t, n=name: has(t, rf"\b{re.escape(n)}\b")))
        out.append((sheet, f"service area {area['name']} (ZIP codes {area['zipPrefixFrom']}–{area['zipPrefixTo']})",
                    lambda t, a=area: has(t, re.escape(a["name"])) and has(t, zips)))

    def payout_lines(t: str) -> list[str]:
        return lines_with(t, r"stripe")

    out += [
        ("vendor", f"Stripe payouts are {pay['cadence']}",
         lambda t: any(has(l, re.escape(pay["cadence"])) for l in payout_lines(t))),
        ("vendor", f"Stripe payout minimum ${pay['minimumUsd']}",
         lambda t: any(has(l, rf"\${pay['minimumUsd']}\b") for l in payout_lines(t))),
        ("vendor", f"Stripe pays a session once it is {pay['settlingDays']} days old",
         lambda t: any(has(l, rf"\b{pay['settlingDays']}[- ]days?\b") for l in payout_lines(t))),
        ("vendor", f"under ${pay['minimumUsd']} rolls over to the next month" if pay["belowMinimumRollsOver"] else "no rollover",
         lambda t: (not pay["belowMinimumRollsOver"]) or any(has(l, r"roll(s|ed|ing)? over") for l in payout_lines(t))),
        ("vendor", f'vendor cost: "{facts["vendorCost"]["wording"]}"', lambda t: wording in norm(t).lower()),
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://orynquest.com/facts.json")
    ap.add_argument("--file")
    ap.add_argument("--out", default="drift.md")
    args = ap.parse_args()
    if args.file:
        facts = json.loads(Path(args.file).read_text(encoding="utf-8"))
        source = args.file
    else:
        req = urllib.request.Request(args.url, headers={"User-Agent": "oryn-blog-content facts-drift (GitHub Actions)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                facts = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                print(f"::notice title=facts.json not live yet::{args.url} answers 404 — it ships with the next site release. Skipping.")
                output("status", "skipped")
                return 0
            raise
        source = args.url
    if facts.get("schema") != "oryn-public-facts/1":
        print(f"::warning::{source} has schema {facts.get('schema')!r}; this checker reads oryn-public-facts/1")
    texts = {k: norm(p.read_text(encoding="utf-8")) for k, p in SHEETS.items()}
    drift = []
    passed = 0
    for sheet, what, test in checks(facts):
        if test(texts[sheet]):
            passed += 1
        else:
            drift.append(f"- `{SHEETS[sheet]}` does not state: {what}")
    print(f"{passed} facts match; {len(drift)} drifted (source: {source}).")
    for line in drift:
        print(line)
    Path(args.out).write_text("\n".join(drift) + ("\n" if drift else ""), encoding="utf-8")
    output("status", "drift" if drift else "ok")
    output("count", str(len(drift)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
