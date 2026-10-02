#!/usr/bin/env python3
"""Shadow-mode ledger for the Agency Hub gates (QUEST, 2 Oct 2026).

For every closed Agency Hub pull request (branch agencyhub/*), record what the
gates said and what a person then did, as one JSON line in
ledger/gate-ledger.jsonl on the unprotected `gate-ledger` branch, and rebuild
ledger/STREAK.md: the run of consecutive agreements per folder, against the
switch-off bar in the plan (15 in a row, zero "too loose").

What the gates said: the hidden `<!-- gate-verdict: pass|fail -->` comment that
auto-merge-agencyhub.yml leaves, taken for the Hub's OWN last version (before
any person changed it). With no such comment (a pull request opened before
shadow mode) the verdict is recomputed with today's rules from main.

Agreement:
  - gates pass, a person merged it without changing it            → agree
  - gates fail, a person closed it, or changed it before merging  → agree
  - gates fail, a person merged it unchanged                      → disagree: too strict
  - gates pass, a person closed it or changed it before merging   → disagree: too loose
    (the dangerous kind: the gates would have let it through)
A merge or close by the Hub itself or by a workflow is not a person's call and
is not counted. Label a pull request `ledger-skip` when a person closes it for
a reason that is not about the post (a duplicate, superseded) — not counted.

Reads pull requests through the API as data. Never checks out pull-request code.

  gate_ledger.py record --pr N [--backfill] [--dry-run]
  gate_ledger.py backfill --from 1 --to 32 [--dry-run]
  gate_ledger.py streak --ledger ledger/gate-ledger.jsonl --out ledger/STREAK.md
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "OrynQuest/oryn-blog-content")
HUB = "AceWattGit"
BOTS = {"github-actions[bot]", "github-actions", "app/github-actions", HUB}
BRANCH = "gate-ledger"
LEDGER = "ledger/gate-ledger.jsonl"
STREAK = "ledger/STREAK.md"
BAR = 15
CHECK_POST = Path(__file__).with_name("check-post.sh")
MARKER = re.compile(r"<!--\s*gate-verdict:\s*(pass|fail)\s*-->")
HEAD_MARKER = re.compile(r"<!--\s*gate-head:\s*([0-9a-f]{40})\s*-->")
FOLDERS = [("vendors", "vendors/ — new posts"), ("parents", "parents/ — new posts"), ("edits", "edits to live posts (text or images)")]


def sh(*cmd: str, check: bool = True, cwd: str | None = None) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout


def api(path: str, paginate: bool = False):
    args = ["gh", "api", f"repos/{REPO}/{path}"]
    if paginate:
        args.insert(2, "--paginate")
        # --paginate concatenates JSON arrays page by page; --slurp joins them.
        args.insert(3, "--slurp")
        pages = json.loads(sh(*args) or "[]")
        return [item for page in pages for item in page]
    return json.loads(sh(*args) or "null")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ── the gates' verdict, recomputed (for pull requests from before shadow mode) ──
def front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return ""
    out = []
    for line in lines[1:]:
        if line == "---":
            break
        out.append(line)
    return "\n".join(out)


def recompute(files: list[dict], sha: str) -> list[str]:
    """The content half of auto-merge-agencyhub.yml (contract + check-post.sh),
    without the hold-for-a-person policy lines."""
    problems: list[str] = []
    for f in files:
        name, status = f["filename"], f["status"]
        if not (re.match(r"^(parents|vendors)/[^/]+\.md$", name) or re.match(r"^public/blog/[^/]+\.(png|jpe?g|webp)$", name)):
            problems.append(f"- {name} is outside parents/, vendors/ or public/blog/")
        if status not in ("added", "modified"):
            problems.append(f"- {name}: {status} is not allowed (only add or modify)")
        if not name.endswith(".md") or status == "removed":
            continue
        blob = api(f"contents/{name}?ref={sha}")
        text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
        fm = front_matter(text)
        for key in ("title", "description", "date"):
            if not re.search(rf"^{key}:[ \t]*\S", fm, re.M):
                problems.append(f"- {name}: front-matter is missing {key}")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp.write(text)
        out = sh("bash", str(CHECK_POST), tmp.name, name, check=False).strip()
        os.unlink(tmp.name)
        problems += [l for l in out.splitlines() if l.strip()]
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", Path(name).stem):
            problems.append(f"- {name}: slug must be lowercase words joined by hyphens")
    return problems


# ── one pull request → one ledger row ────────────────────────────────────────
def build_row(num: int, backfill: bool) -> dict | None:
    pr = api(f"pulls/{num}")
    if not pr["head"]["ref"].startswith("agencyhub/"):
        print(f"#{num}: not an Agency Hub pull request ({pr['head']['ref']}) — skipped")
        return None
    if pr["state"] != "closed":
        print(f"#{num}: still open — skipped")
        return None
    commits = api(f"pulls/{num}/commits", paginate=True)
    # The Hub's own last version: its commits up to the first one a person made.
    hub_head = None
    for c in commits:
        who = (c.get("author") or {}).get("login") or c["commit"]["author"]["name"]
        if who != HUB:
            break
        hub_head = c["sha"]
    final_head = pr["head"]["sha"]
    edited = False
    if hub_head and hub_head != final_head:
        diff = api(f"compare/{hub_head}...{final_head}")
        edited = bool(diff.get("files"))
    files = api(f"pulls/{num}/files", paginate=True) if (hub_head in (None, final_head)) else (
        api(f"compare/{pr['base']['sha']}...{hub_head}").get("files", [])
    )
    files = [{"filename": f["filename"], "status": f["status"]} for f in files]

    comments = api(f"issues/{num}/comments", paginate=True)
    markers = []
    for c in comments:
        if (c.get("user") or {}).get("login") != "github-actions[bot]":
            continue
        m = MARKER.search(c.get("body") or "")
        if m:
            h = HEAD_MARKER.search(c["body"])
            markers.append((m.group(1), h.group(1) if h else None))
    gate, source, problems = None, None, []
    on_hub = [v for v, h in markers if h and h == hub_head]
    if on_hub:
        gate, source = on_hub[-1], "marker on the Hub's version"
    elif markers and not edited:
        gate, source = markers[-1][0], "last marker"
    if gate is None or backfill:
        sha = hub_head or final_head
        problems = recompute(files, sha)
        if gate is None:
            gate, source = ("fail" if problems else "pass"), f"recomputed with today's rules at {sha[:7]}"
    gate_at_head = None
    if backfill and edited:
        head_files = [{"filename": f["filename"], "status": f["status"]} for f in api(f"pulls/{num}/files", paginate=True)]
        gate_at_head = "fail" if recompute(head_files, final_head) else "pass"

    merged = bool(pr.get("merged_at"))
    events = api(f"issues/{num}/events", paginate=True)
    closers = [e["actor"]["login"] for e in events if e.get("event") == "closed" and e.get("actor")]
    decider = (pr.get("merged_by") or {}).get("login") if merged else (closers[-1] if closers else os.environ.get("SENDER", ""))
    decider = decider or (closers[-1] if closers else "unknown")
    human = decider not in BOTS
    labels = [l["name"] for l in pr.get("labels", [])]
    md = [f for f in files if f["filename"].endswith(".md")]
    if any(f["status"] == "modified" for f in files) or not md:
        folder = "edits"
    else:
        folder = md[0]["filename"].split("/")[0]
    outcome = "merged" if merged else "closed"
    if not human:
        agreement, counted = f"not counted: decided by {decider}", False
    elif "ledger-skip" in labels:
        agreement, counted = "not counted: labelled ledger-skip (not about the post)", False
    elif outcome == "merged" and not edited:
        agreement, counted = ("agree" if gate == "pass" else "disagree: too strict"), True
    elif outcome == "merged":
        agreement, counted = ("agree" if gate == "fail" else "disagree: too loose"), True
    else:
        agreement, counted = ("agree" if gate == "fail" else "disagree: too loose"), True
    row = {
        "pr": num,
        "title": pr["title"],
        "branch": pr["head"]["ref"],
        "folder": folder,
        "files": [f["filename"] for f in files],
        "hub_head": hub_head,
        "final_head": final_head,
        "gate": gate,
        "gate_source": source,
        "gate_problems": problems[:12],
        "outcome": outcome,
        "decider": decider,
        "human": human,
        "edited_by_person": edited,
        "agreement": agreement,
        "counted": counted and not backfill,
        "closed_at": pr["closed_at"],
        "recorded_at": now_iso(),
        "backfill": backfill,
    }
    if gate_at_head is not None:
        row["gate_at_final_head"] = gate_at_head
    return row


# ── STREAK.md ────────────────────────────────────────────────────────────────
def latest_per_pr(rows: list[dict]) -> list[dict]:
    seen: dict[int, dict] = {}
    for r in sorted(rows, key=lambda r: (r.get("closed_at") or "", r.get("recorded_at") or "")):
        seen[r["pr"]] = r
    return sorted(seen.values(), key=lambda r: r.get("closed_at") or "")


def streak_md(rows: list[dict]) -> str:
    live = latest_per_pr([r for r in rows if not r.get("backfill")])
    back = latest_per_pr([r for r in rows if r.get("backfill")])
    out = [
        "# Gate ledger — shadow-mode streak",
        "",
        f"_Rebuilt {now_iso()} by .github/scripts/gate_ledger.py from `{LEDGER}` "
        f"({len(live)} live decisions, {len(back)} backfilled)._",
        "",
        "**Switch-off bar** (Agency Hub — Full Automation Plan, 2 Oct 2026): the gates must match a person's call on "
        f"**{BAR} posts in a row, with zero \"too loose\"** (a post the gates passed that a person then stopped or changed). "
        "Only then does `HOLD_NEW_POSTS` turn off for that folder — vendors/ first, then parents/, then edits. "
        "A miss resets the count; the fix is a new gate.",
        "",
        "| Folder | Current streak | Bar | Too loose in the streak | Too loose ever | Too strict ever | Person decisions counted | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label in FOLDERS:
        mine = [r for r in live if r["folder"] == key and r.get("counted")]
        streak = 0
        for r in reversed(mine):
            if r["agreement"] != "agree":
                break
            streak += 1
        loose = sum(1 for r in mine if r["agreement"] == "disagree: too loose")
        strict = sum(1 for r in mine if r["agreement"] == "disagree: too strict")
        status = "**READY** — a person may switch the hold off" if streak >= BAR else "not yet"
        out.append(f"| {label} | {streak} | {min(streak, BAR)}/{BAR} | 0 | {loose} | {strict} | {len(mine)} | {status} |")
    out += ["", "## Last live decisions", ""]
    if live:
        out += ["| PR | Folder | Gates | Person | Edited first | Result |", "|---|---|---|---|---|---|"]
        for r in live[-20:][::-1]:
            out.append(f"| #{r['pr']} | {r['folder']} | {r['gate']} | {r['outcome']} by {r['decider']} | {'yes' if r['edited_by_person'] else 'no'} | {r['agreement']} |")
    else:
        out.append("None yet — the first Agency Hub pull request closed after 2 Oct 2026 starts the count.")
    out += [
        "",
        "## Backfill (pull requests before shadow mode — NOT counted)",
        "",
        "Verdicts recomputed with the rules on main on the day of the backfill (`.github/scripts/check-post.sh` + the "
        "contract), run on the Hub's own last version of each pull request. They show how today's gates would have "
        "judged the past; they never count toward the bar.",
        "",
    ]
    if back:
        agree = sum(1 for r in back if r["agreement"] == "agree")
        loose = sum(1 for r in back if r["agreement"] == "disagree: too loose")
        strict = sum(1 for r in back if r["agreement"] == "disagree: too strict")
        people = sum(1 for r in back if r["human"] and "ledger-skip" not in r["agreement"])
        out += [f"Of {people} person decisions: {agree} agree, {loose} too loose, {strict} too strict.", "",
                "| PR | Folder | Gates (today's rules) | Person | Edited first | Result |", "|---|---|---|---|---|---|"]
        for r in back:
            out.append(f"| #{r['pr']} | {r['folder']} | {r['gate']} | {r['outcome']} by {r['decider']} | {'yes' if r['edited_by_person'] else 'no'} | {r['agreement']} |")
    return "\n".join(out) + "\n"


# ── writing to the gate-ledger branch ────────────────────────────────────────
def publish(new_rows: list[dict], message: str) -> None:
    """Append rows on the gate-ledger branch and rebuild STREAK.md; retries when
    another run pushed first. Uses a git worktree of this checkout, so the
    workflow's push credentials carry over."""
    for attempt in range(6):
        work = tempfile.mkdtemp(prefix="gate-ledger-")
        os.rmdir(work)
        try:
            exists = sh("git", "ls-remote", "--heads", "origin", BRANCH).strip() != ""
            if exists:
                sh("git", "fetch", "--quiet", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}")
                sh("git", "worktree", "add", "--quiet", "--detach", work, f"origin/{BRANCH}")
            else:
                sh("git", "worktree", "add", "--quiet", "--detach", work)
                sh("git", "checkout", "--quiet", "--orphan", BRANCH, cwd=work)
                sh("git", "rm", "-rf", "--quiet", ".", cwd=work)
            ledger = Path(work, LEDGER)
            ledger.parent.mkdir(parents=True, exist_ok=True)
            rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()] if ledger.exists() else []
            have = {(r["pr"], r.get("closed_at"), r.get("backfill", False)) for r in rows}
            added = [r for r in new_rows if (r["pr"], r.get("closed_at"), r.get("backfill", False)) not in have]
            if not added:
                print("Ledger already has these rows — nothing to add.")
                return
            with ledger.open("a", encoding="utf-8") as fh:
                for r in added:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            rows += added
            Path(work, STREAK).write_text(streak_md(rows), encoding="utf-8")
            readme = Path(work, "README.md")
            if not readme.exists():
                readme.write_text(
                    "# gate-ledger\n\nShadow-mode ledger of the Agency Hub gates. Written only by "
                    ".github/workflows/gate-ledger.yml (on main). One JSON line per closed Agency Hub pull request in "
                    f"`{LEDGER}`; the streak in `{STREAK}`. Not part of the site.\n",
                    encoding="utf-8",
                )
            sh("git", "add", "-A", cwd=work)
            sh("git", "commit", "--quiet", "-m", message + os.environ.get("LEDGER_COMMIT_TRAILER", ""), cwd=work)
            res = subprocess.run(["git", "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"], cwd=work, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"Pushed {len(added)} row(s) to {BRANCH}.")
                return
            print(f"Push rejected (attempt {attempt + 1}): {res.stderr.strip()[:200]} — retrying")
            time.sleep(3 + attempt * 2)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", work], capture_output=True)
            shutil.rmtree(work, ignore_errors=True)
    raise SystemExit("Could not push to the gate-ledger branch after 6 attempts")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--pr", type=int, required=True)
    r.add_argument("--backfill", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    b = sub.add_parser("backfill")
    b.add_argument("--from", dest="lo", type=int, default=1)
    b.add_argument("--to", dest="hi", type=int, default=32)
    b.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("streak")
    s.add_argument("--ledger", required=True)
    s.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "streak":
        rows = [json.loads(l) for l in Path(args.ledger).read_text().splitlines() if l.strip()]
        Path(args.out).write_text(streak_md(rows), encoding="utf-8")
        return 0
    if args.cmd == "record":
        row = build_row(args.pr, args.backfill)
        if row is None:
            return 0
        print(json.dumps(row, indent=2, ensure_ascii=False))
        if not args.dry_run:
            publish([row], f"ledger: PR #{args.pr} — gates {row['gate']}, {row['outcome']} by {row['decider']} → {row['agreement']}")
        return 0
    rows = []
    for num in range(args.lo, args.hi + 1):
        try:
            row = build_row(num, backfill=True)
        except Exception as err:  # a pull request whose files can no longer be read
            print(f"#{num}: could not infer a verdict ({err}) — skipped")
            continue
        if row:
            print(f"#{num}: gates {row['gate']} ({len(row['gate_problems'])} problems), {row['outcome']} by {row['decider']}, edited={row['edited_by_person']} → {row['agreement']}")
            rows.append(row)
    if not args.dry_run and rows:
        publish(rows, f"ledger: backfill PRs #{args.lo}–#{args.hi} with today's rules (not counted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
