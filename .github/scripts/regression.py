#!/usr/bin/env python3
"""Golden-set regression (QUEST, 2 Oct 2026 — criteria/criteria.md, Part D).

Replays every case in criteria/golden/ through .github/scripts/check-post.sh:
  - a known-bad case (expected: fail) must FAIL the check;
  - a known-good case (expected: pass) must PASS it.
Then compares with criteria/lessons.jsonl:
  - REGRESSION   a closed lesson whose bad text passes again   → the run fails
  - FALSE ALARM  a known-good case the check now rejects        → the run fails
  - OPEN (QUEST) a lesson a rule could catch but none does yet
  - OPEN (HUB)   a lesson only Jev, the image judge or the real-world gate can catch

  regression.py [--write] [--out report.md]
--write sets each lesson's `closed` from this run and rebuilds criteria/LESSONS.md
(run it by hand before committing a new rule or lesson). Writes
`status`, `misses`, `regressions`, `false_alarms` to $GITHUB_OUTPUT when set.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "criteria" / "golden"
LESSONS = ROOT / "criteria" / "lessons.jsonl"
LESSONS_MD = ROOT / "criteria" / "LESSONS.md"
CHECK = ROOT / ".github" / "scripts" / "check-post.sh"
CATCH_LABEL = {"rules": "check-post.sh", "jev": "Jev (judged criteria)", "vision": "the Hub image judge (vision)", "real-world": "the Hub real-world gate"}


def parse_case(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    assert lines[0] == "---", f"{path}: no front-matter"
    end = lines.index("---", 1)
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value)
        meta[key.strip()] = value
    meta["excerpt"] = "\n".join(lines[end + 1:]).strip()
    meta["file"] = path.relative_to(ROOT).as_posix()
    return meta


def run_check(case: dict) -> list[str]:
    """The excerpt as a post: in the body, or as the hero's alt text."""
    if case.get("field") == "imageAlt":
        alt = case["excerpt"].replace('"', "'")
        post = f'---\nimage: /blog-assets/golden-case.jpg\nimageAlt: "{alt}"\n---\n'
    else:
        post = case["excerpt"] + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(post)
    try:
        out = subprocess.run(["bash", str(CHECK), tmp.name, case["file"]], capture_output=True, text=True).stdout
    finally:
        os.unlink(tmp.name)
    return [l for l in out.splitlines() if l.strip()]


def lessons_md(lessons: list[dict], results: dict[str, dict]) -> str:
    closed = sum(1 for l in lessons if l["closed"])
    rows = [
        "# Lessons — every mistake once, never twice",
        "",
        "Generated from `criteria/lessons.jsonl` by `.github/scripts/regression.py --write`; do not edit by hand.",
        "A lesson is **closed** only when its original bad text now FAILS the check named in `check`",
        "(replayed from `criteria/golden/` on every change by `.github/workflows/regression.yml`).",
        "",
        f"**{closed} of {len(lessons)} closed.** Open lessons owned by HUB need Jev, the image judge or the real-world gate.",
        "",
        "| Lesson | Date | Rule | Owner | Caught by | Closed | Golden case |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in lessons:
        rows.append(
            f"| {l['id']} | {l['date']} | {l['right_rule'].replace('|', '/')} | {l['owner']} | {l['check']} | "
            f"{'yes' if l['closed'] else '**no**'} | [{Path(l['golden']).stem}](golden/{Path(l['golden']).name}) |"
        )
    rows += ["", "## The wrong text, as it was written", ""]
    for l in lessons:
        wrong = " ".join(l["wrong_text"].split())
        rows.append(f"- **{l['id']}** — “{wrong[:300]}{'…' if len(wrong) > 300 else ''}” — {l['source']}. Trigger: {l['trigger']}.")
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cases = [parse_case(p) for p in sorted(GOLDEN.glob("*.md"))]
    lessons = [json.loads(l) for l in LESSONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_lesson = {l["id"]: l for l in lessons}
    results: dict[str, dict] = {}
    for case in cases:
        hits = run_check(case)
        results[case["id"]] = {"case": case, "caught": bool(hits), "hits": hits}

    bad = [r for r in results.values() if r["case"]["expected"] == "fail"]
    good = [r for r in results.values() if r["case"]["expected"] == "pass"]
    caught = [r for r in bad if r["caught"]]
    false_alarms = [r for r in good if r["caught"]]
    regressions, open_quest, open_hub, closable = [], [], [], []
    for r in bad:
        if r["caught"]:
            lesson = by_lesson.get(r["case"].get("lesson", ""))
            if lesson and not lesson["closed"]:
                closable.append(r)
            continue
        lesson = by_lesson.get(r["case"].get("lesson", ""), {})
        if lesson.get("closed"):
            regressions.append(r)
        elif r["case"].get("catch", "rules") != "rules" or lesson.get("owner") == "HUB":
            open_hub.append(r)
        else:
            open_quest.append(r)
    unknown = [c["id"] for c in cases if c["expected"] == "fail" and c.get("lesson") not in by_lesson]

    def line(r: dict) -> str:
        c = r["case"]
        tag = f"{c.get('lesson', '—')} · " if c["expected"] == "fail" else ""
        return f"- {tag}[`{c['id']}`]({c['file']}) — {c['rule']} _Source: {c['source']}_"

    report = [
        f"**Deterministic gate (`check-post.sh`) on the golden set:** catches **{len(caught)} of {len(bad)}** known-bad cases; "
        f"passes **{len(good) - len(false_alarms)} of {len(good)}** known-good cases.",
        "",
    ]
    if regressions:
        report += ["### Regressions — a closed lesson's bad text passes again (fix the rule)", ""] + [line(r) for r in regressions] + [""]
    if false_alarms:
        report += ["### False alarms — known-good text the check now rejects (fix the rule)", ""]
        report += [line(r) + "\n  - " + "\n  - ".join(h[:200] for h in r["hits"]) for r in false_alarms] + [""]
    if open_quest:
        report += ["### Not yet automated (owner: QUEST — a rule can catch these)", ""] + [line(r) for r in open_quest] + [""]
    if open_hub:
        report += ["### Need Jev, the image judge or the real-world gate (owner: HUB)", ""]
        report += [line(r) + f" — needs {CATCH_LABEL.get(r['case'].get('catch', 'rules'), 'Jev')}" for r in open_hub] + [""]
    if closable:
        report += ["### Now caught but still marked open (run `regression.py --write` and commit)", ""] + [line(r) for r in closable] + [""]
    if unknown:
        report += ["### Known-bad cases with no lesson in criteria/lessons.jsonl", ""] + [f"- `{u}`" for u in unknown] + [""]
    text = "\n".join(report)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")

    if args.write:
        for l in lessons:
            res = next((r for r in bad if r["case"].get("lesson") == l["id"]), None)
            l["closed"] = bool(res and res["caught"])
        LESSONS.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lessons), encoding="utf-8")
        LESSONS_MD.write_text(lessons_md(lessons, results), encoding="utf-8")
        print(f"Wrote {LESSONS.relative_to(ROOT)} and {LESSONS_MD.relative_to(ROOT)}.")

    misses = len(regressions) + len(open_quest) + len(open_hub)
    status = "broken" if (regressions or false_alarms) else ("misses" if misses or unknown else "clean")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"status={status}\nmisses={misses}\nregressions={len(regressions)}\nfalse_alarms={len(false_alarms)}\n"
                     f"caught={len(caught)}\nbad={len(bad)}\ngood_passed={len(good) - len(false_alarms)}\ngood={len(good)}\n")
    return 1 if (regressions or false_alarms) else 0


if __name__ == "__main__":
    sys.exit(main())
