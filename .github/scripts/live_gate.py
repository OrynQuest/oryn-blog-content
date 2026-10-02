#!/usr/bin/env python3
"""Live gate (gate 5 of the Agency Hub automation plan, QUEST, 2 Oct 2026).

After a post is added or changed on main, fetch https://orynquest.com/blog/<slug>
the way search and answer engines do (as Googlebot and as GPTBot) and check it:
HTTP 200, the post's title (or seoTitle) in a <title>, not a "not found" page,
and not hidden from search (noindex). If it still fails once the site has had
time to refresh, revert the commit that added or changed it (through a pull
request, merged with the workflow's token) and open an issue with the evidence.

Safety rules (all must hold before anything is reverted):
  - the site itself is healthy (the blog index and another live post pass), so
    a site-wide outage never reverts a good post;
  - the commit being reverted is the one that added or changed THIS post (and
    touches nothing but failing posts and blog images);
  - it is not itself a revert (never revert a revert);
  - nobody changed the post on main since that commit;
  - no auto-revert for this post yet today (so it can never loop).

Reads only this repository's own main branch and the public website. It never
checks out or runs pull-request code.

Usage (the workflow passes these; run it by hand with --mode dry-run):
  live_gate.py --before <sha> --after <sha> [--mode live|dry-run|rehearsal]
               [--simulate-fail] [--paths "parents/a.md vendors/b.md"]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = os.environ.get("LIVE_BASE_URL", "https://orynquest.com").rstrip("/")
USER_AGENTS = {
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
}
# Today the site may stream <title> into <body> for bots, so a <title> anywhere
# in the page counts. Once the release that keeps <title> in <head> ships, set
# REQUIRE_TITLE_IN_HEAD: "true" in .github/workflows/live-check.yml.
REQUIRE_TITLE_IN_HEAD = os.environ.get("REQUIRE_TITLE_IN_HEAD", "false").lower() == "true"
# First look: retry for about 3 minutes while the push webhook refreshes the site.
MAX_WAIT_SECONDS = int(os.environ.get("LIVE_MAX_WAIT_SECONDS", "180"))
RETRY_EVERY_SECONDS = int(os.environ.get("LIVE_RETRY_EVERY_SECONDS", "20"))
# Second look before reverting anything: the site's blog cache refreshes on its
# own every 600 s (src/lib/blog/source.ts REVALIDATE_SECONDS) if a webhook is
# missed, so one more check 11 minutes after the start rules out a stale cache.
SECOND_LOOK_AFTER_SECONDS = int(os.environ.get("LIVE_SECOND_LOOK_AFTER_SECONDS", "660"))
REPO = os.environ.get("GITHUB_REPOSITORY", "OrynQuest/oryn-blog-content")
RUN_URL = (
    f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{REPO}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    if os.environ.get("GITHUB_RUN_ID")
    else "(local run)"
)
NOT_FOUND = re.compile(r"\b(page|post) not found\b", re.I)


# ── small helpers ────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(msg, flush=True)


def sh(*cmd: str, check: bool = True) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        shown = " ".join(cmd[:5]) + (" …" if len(cmd) > 5 else "")
        raise RuntimeError(f"{shown} failed ({res.returncode}): {(res.stderr.strip() or res.stdout.strip())[:300]}")
    return res.stdout.strip()


def git(*args: str, check: bool = True) -> str:
    return sh("git", *args, check=check)


def front_matter(text: str) -> dict[str, str]:
    """The same reading check-post.sh does: first `key: value` wins, quotes and
    trailing comments stripped."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
        if not m or m.group(1) in out:
            continue
        value = m.group(2).strip()
        if value[:1] in ('"', "'") and len(value) >= 2 and value.endswith(value[0]):
            value = value[1:-1]
            if m.group(2).strip().startswith('"'):
                value = value.replace('\\"', '"')
        else:
            value = re.sub(r"\s+#.*$", "", value)
        out[m.group(1)] = value
    return out


def norm(text: str) -> str:
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-"})
    return re.sub(r"\s+", " ", text).strip().lower()


def title_matches(page_title: str, candidates: list[str]) -> bool:
    shown = norm(page_title)
    shown = re.sub(r"\s*\|\s*oryn quest$", "", shown)
    for cand in candidates:
        want = norm(cand)
        if not want:
            continue
        if want in shown:
            return True
        # The site cuts a long title at a word and adds "…" (src/lib/seo/fitText.ts).
        if shown.endswith("…"):
            stem = shown[:-1].rstrip()
            if len(stem) >= 15 and want.startswith(stem):
                return True
    return False


def visible_text(page: str) -> str:
    page = re.sub(r"<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>", " ", page, flags=re.I | re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


def fetch(url: str, user_agent: str) -> tuple[int, str, str, str | None]:
    req = urllib.request.Request(
        url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            return res.status, res.geturl(), res.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace") if err.fp else ""
        return err.code, url, body, None
    except Exception as err:  # network error, timeout
        return 0, url, "", f"{type(err).__name__}: {err}"


def check_page(url: str, ua_name: str, candidates: list[str], source_says_not_found: bool) -> dict:
    status, final_url, page, error = fetch(url, USER_AGENTS[ua_name])
    titles = re.findall(r"<title\b[^>]*>(.*?)</title\s*>", page, flags=re.I | re.S)
    head_end = page.lower().find("</head>")
    head_titles = re.findall(r"<title\b[^>]*>(.*?)</title\s*>", page[:head_end], flags=re.I | re.S) if head_end >= 0 else []
    pool = head_titles if REQUIRE_TITLE_IN_HEAD else titles
    title_ok = any(title_matches(t, candidates) for t in pool)
    not_found = any(NOT_FOUND.search(norm(t)) for t in titles) or (
        not source_says_not_found and bool(NOT_FOUND.search(visible_text(page)))
    )
    noindex = bool(
        re.search(r"<meta\b[^>]*name=[\"'](robots|googlebot)[\"'][^>]*content=[\"'][^\"']*noindex", page, re.I)
        or re.search(r"<meta\b[^>]*content=[\"'][^\"']*noindex[^\"']*[\"'][^>]*name=[\"'](robots|googlebot)[\"']", page, re.I)
    )
    problems = []
    if error:
        problems.append(f"fetch error: {error}")
    elif status != 200:
        problems.append(f"HTTP {status}")
    if not title_ok:
        where = "in <head>" if REQUIRE_TITLE_IN_HEAD else "in any <title>"
        problems.append(f"post title not found {where}")
    if not_found:
        problems.append('page says "not found"')
    if noindex:
        problems.append("page is marked noindex (hidden from search)")
    return {
        "ua": ua_name,
        "url": url,
        "status": status,
        "final_url": final_url,
        "titles_seen": [html.unescape(t).strip()[:120] for t in titles[:3]],
        "title_in_head": any(title_matches(t, candidates) for t in head_titles),
        "ok": not problems,
        "problems": problems,
    }


# ── checking posts ───────────────────────────────────────────────────────────
def load_post(path: str) -> dict:
    p = Path(path)
    slug = p.name[:-3] if p.name.endswith(".md") else p.name
    text = p.read_text(encoding="utf-8") if p.is_file() else ""
    fm = front_matter(text)
    seo = fm.get("seoTitle") or fm.get("seo_title") or fm.get("metaTitle") or fm.get("meta_title") or ""
    return {
        "path": path,
        "slug": slug,
        "exists": p.is_file(),
        "title": fm.get("title", ""),
        "seoTitle": seo,
        "draft": fm.get("draft", "").strip().lower() == "true",
        "source_says_not_found": bool(NOT_FOUND.search(text)),
    }


def check_round(posts: list[dict], simulate_fail: bool) -> None:
    for post in posts:
        if post.get("ok"):
            continue
        url = f"{BASE_URL}/blog/{post['slug']}"
        if simulate_fail:
            url += "-live-check-simulated-404"  # a guaranteed 404, for tests only
        checks = [
            check_page(url, ua, [post["title"], post["seoTitle"]], post["source_says_not_found"])
            for ua in USER_AGENTS
        ]
        post["checks"] = checks
        post["ok"] = all(c["ok"] for c in checks)
        post["attempts"] = post.get("attempts", 0) + 1


def run_checks(posts: list[dict], simulate_fail: bool, test_mode: bool) -> None:
    start = time.monotonic()
    while True:
        check_round(posts, simulate_fail)
        pending = [p for p in posts if not p["ok"]]
        for p in posts:
            state = "PASS" if p["ok"] else "not yet"
            log(f"  [{int(time.monotonic() - start):>4}s] {state}: {p['slug']}"
                + ("" if p["ok"] else " — " + "; ".join(f"{c['ua']}: {', '.join(c['problems'])}" for c in p["checks"] if not c["ok"])))
        if not pending or time.monotonic() - start >= MAX_WAIT_SECONDS:
            break
        time.sleep(RETRY_EVERY_SECONDS)
    pending = [p for p in posts if not p["ok"]]
    if pending and not test_mode:
        wait = SECOND_LOOK_AFTER_SECONDS - (time.monotonic() - start)
        if wait > 0:
            log(f"Second look in {int(wait)} s (rules out a missed webhook / stale site cache) …")
            time.sleep(wait)
        check_round(posts, simulate_fail)
    elif pending:
        log("Second look skipped (test mode).")


def control_healthy(skip_paths: set[str]) -> tuple[bool, str]:
    """Is the site itself fine? The blog index answers 200 and another live post passes."""
    status, _, _, err = fetch(f"{BASE_URL}/blog", USER_AGENTS["Googlebot"])
    if status != 200:
        return False, f"the blog index {BASE_URL}/blog answered HTTP {status}{' (' + err + ')' if err else ''}"
    for path in sorted(Path("parents").glob("*.md")) + sorted(Path("vendors").glob("*.md")):
        sp = path.as_posix()
        if sp in skip_paths:
            continue
        post = load_post(sp)
        if post["draft"] or not post["title"]:
            continue
        res = check_page(f"{BASE_URL}/blog/{post['slug']}", "Googlebot", [post["title"], post["seoTitle"]], post["source_says_not_found"])
        if res["ok"]:
            return True, f"the blog index and {post['slug']} pass"
    return False, "no other live post passes either (site-wide problem)"


# ── deciding and reverting ───────────────────────────────────────────────────
def is_revert(sha: str) -> bool:
    msg = git("log", "-1", "--format=%B", sha)
    subject = msg.splitlines()[0] if msg else ""
    return bool(
        re.match(r'^(\[rehearsal\] )?(Revert "|Auto-revert:|Revert:)', subject)
        or "This reverts commit" in msg
    )


def first_parent_diff(sha: str) -> list[str]:
    parents = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
    if not parents:
        return git("show", "--name-only", "--format=", sha).splitlines()
    return git("diff", "--name-only", parents[0], sha).splitlines()


def reverted_today(slug: str, rehearsal: bool) -> bool:
    title = f"Auto-revert: {slug} failed the live check"
    if rehearsal:
        title = "[rehearsal] " + title
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = sh("gh", "pr", "list", "--repo", REPO, "--state", "all", "--limit", "100",
             "--search", f'"failed the live check" in:title created:>={today}',
             "--json", "title", "--jq", ".[].title", check=False)
    return title in out.splitlines()


def decide(post: dict, before: str, after: str, failing: set[str], rehearsal: bool) -> tuple[str | None, str]:
    """Returns (commit to revert, reason) — commit None means: do not revert."""
    rng = f"{before}..{after}" if before else f"{after}^!"
    shown = f"{before[:7]}..{after[:7]}" if before else after[:7]
    target = git("log", "-1", "--first-parent", "--format=%H", rng, "--", post["path"], check=False)
    if not target:
        return None, f"no commit in {shown} added or changed {post['path']}, so there is nothing of this push to revert"
    if is_revert(target):
        return None, f"{target[:7]} is itself a revert — never revert a revert"
    files = first_parent_diff(target)
    others = [f for f in files if f not in failing and not f.startswith("public/blog/")]
    if others:
        return None, f"{target[:7]} also changes {', '.join(others[:5])}{' …' if len(others) > 5 else ''} — a person must decide"
    git("fetch", "--quiet", "origin", "main")
    if subprocess.run(["git", "diff", "--quiet", target, "origin/main", "--", post["path"]]).returncode != 0:
        return None, f"{post['path']} changed on main after {target[:7]} — a person must decide"
    if reverted_today(post["slug"], rehearsal):
        return None, f"{post['slug']} was already auto-reverted today (at most once a day)"
    return target, f"{target[:7]} added or changed {post['path']}"


def run_mutation(dry: bool, *cmd: str) -> str:
    if dry:
        log("    DRY RUN would run: " + " ".join(repr(c) if " " in c else c for c in cmd))
        return ""
    return sh(*cmd)


def revert(target: str, slugs: list[str], mode: str, run_id: str, paths: list[str]) -> tuple[str | None, str]:
    """Revert `target` through a pull request merged with the workflow token.

    rehearsal: the same steps against a throwaway copy of main. It commits a
    harmless HTML comment to the post THERE, then reverts that commit with a
    pull request merged with the workflow token, checks the copy is back to
    main, and deletes both branches. main and the website are never touched.
    """
    dry = mode == "dry-run"
    rehearsal = mode == "rehearsal"
    slug_list = ", ".join(slugs)
    title = f"Auto-revert: {slug_list} failed the live check"
    base = "main"
    if rehearsal:
        title = "[rehearsal] " + title
        base = f"live-check-rehearsal-{run_id}"
        git("switch", "--quiet", "-c", base, "origin/main")
        for path in paths:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n<!-- live-check rehearsal: this commit exists only on a throwaway branch -->\n")
        git("add", "--", *paths)
        git("commit", "--quiet", "-m", f"rehearsal: stand-in for the commit that changed {slug_list}")
        git("push", "--quiet", "origin", f"HEAD:refs/heads/{base}")
        target = git("rev-parse", "HEAD")
    short = target[:7]
    branch = f"revert/{short}"
    if not dry and git("ls-remote", "--heads", "origin", branch):
        return None, f"branch {branch} already exists — not reverting twice"
    parents = git("rev-list", "--parents", "-n", "1", target).split()[1:]
    revert_cmd = ["git", "revert", "--no-edit"] + (["-m", "1"] if len(parents) > 1 else []) + [target]
    if dry:
        log(f"    DRY RUN would run: git switch -c {branch} origin/{base} && {' '.join(revert_cmd)} && git push origin {branch}")
    else:
        git("switch", "--quiet", "-c", branch, target if rehearsal else "origin/main")
        res = subprocess.run(revert_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            subprocess.run(["git", "revert", "--abort"], capture_output=True)
            git("switch", "--quiet", "--detach", "origin/main")
            return None, f"git revert {short} did not apply cleanly ({res.stderr.strip()[:200]})"
        git("push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")
    body = (
        f"The live check could not load {slug_list} on {BASE_URL} as Googlebot and GPTBot "
        f"(evidence in the issue and in {RUN_URL}).\n\n"
        f"This reverts {target} — the commit that added or changed it — so the site goes back to the last good state. "
        "Fix the post and publish it again; the live check runs on every push.\n\n"
        "Opened and merged automatically by .github/workflows/live-check.yml (gate 5)."
    )
    pr_url = run_mutation(dry, "gh", "pr", "create", "--repo", REPO, "--base", base, "--head", branch, "--title", title, "--body", body)
    run_mutation(dry, "gh", "pr", "merge", pr_url or "<pr>", "--repo", REPO, "--squash", "--delete-branch")
    if rehearsal:
        git("fetch", "--quiet", "origin", base)
        same = subprocess.run(["git", "diff", "--quiet", "origin/main", f"origin/{base}", "--", *paths]).returncode == 0
        log(f"    rehearsal: after the merge the throwaway branch {'MATCHES' if same else 'DOES NOT MATCH'} main for {', '.join(paths)}")
        git("push", "--quiet", "origin", "--delete", base)
        git("switch", "--quiet", "--detach", "origin/main")
        if not same:
            return None, f"rehearsal revert through {pr_url} did not restore the post"
    elif not dry:
        git("switch", "--quiet", "--detach", "origin/main")
    return pr_url or "(dry run)", f"reverted {short} through {pr_url or 'a pull request (dry run)'}"


def cleanup_after_failure(mode: str, run_id: str) -> None:
    """Leave no half-made branches behind (a rehearsal's throwaway copy of main,
    or a revert branch whose pull request could not be opened)."""
    subprocess.run(["git", "revert", "--abort"], capture_output=True)
    subprocess.run(["git", "switch", "--quiet", "--detach", "origin/main"], capture_output=True)
    if mode == "rehearsal":
        subprocess.run(["git", "push", "--quiet", "origin", "--delete", f"live-check-rehearsal-{run_id}"], capture_output=True)
        for ref in git("ls-remote", "--heads", "origin", "revert/*", check=False).splitlines():
            name = ref.split("refs/heads/")[-1]
            log_msg = git("log", "-1", "--format=%s", ref.split()[0], check=False)
            if "rehearsal" in log_msg or name.endswith(f"-{run_id}"):
                subprocess.run(["git", "push", "--quiet", "origin", "--delete", name], capture_output=True)


def open_issue(post: dict, action: str, mode: str) -> str:
    title = f"Live check failed: {post['slug']}"
    if mode == "rehearsal":
        title = "[rehearsal] " + title
    lines = [
        f"**{BASE_URL}/blog/{post['slug']}** failed the live check after {post.get('attempts', 0)} looks.",
        "",
        "| Crawler | HTTP | Title found | Problems |",
        "|---|---|---|---|",
    ]
    for c in post.get("checks", []):
        found = "yes" if not any("title not found" in p for p in c["problems"]) else "no"
        lines.append(f"| {c['ua']} | {c['status']} | {found} | {'; '.join(c['problems']) or '—'} |")
    seen = sorted({t for c in post.get("checks", []) for t in c["titles_seen"]})
    lines += [
        "",
        f"- Post file: `{post['path']}`{'' if post['exists'] else ' (not in the repository)'}",
        f"- Expected title: {post['title'] or '(none)'}" + (f" / seoTitle: {post['seoTitle']}" if post["seoTitle"] else ""),
        f"- `<title>` seen: {' · '.join(seen) if seen else '(none)'}",
        f"- Title required in `<head>`: {'yes' if REQUIRE_TITLE_IN_HEAD else 'no (accepted anywhere for now)'}",
        f"- What happened: {action}",
        f"- Run: {RUN_URL}",
        "",
        "_Opened by .github/workflows/live-check.yml (gate 5 of the Agency Hub automation plan)._",
    ]
    body = "\n".join(lines)
    if mode == "dry-run":
        log(f"    DRY RUN would open issue '{title}':\n" + "\n".join("      " + l for l in lines))
        return "(dry run)"
    existing = sh("gh", "issue", "list", "--repo", REPO, "--state", "open", "--limit", "100",
                  "--search", f'"{title}" in:title', "--json", "number,title",
                  "--jq", f'.[] | select(.title == {json.dumps(title)}) | .number', check=False).splitlines()
    if existing:
        sh("gh", "issue", "comment", existing[0], "--repo", REPO, "--body", body)
        url = f"https://github.com/{REPO}/issues/{existing[0]}"
    else:
        url = sh("gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body)
    if mode == "rehearsal":
        sh("gh", "issue", "close", url, "--repo", REPO, "--comment", "Rehearsal only — nothing on main was changed.")
    return url


# ── main ─────────────────────────────────────────────────────────────────────
def changed_posts(before: str, after: str) -> list[str]:
    if before:
        out = git("diff", "--name-status", "--no-renames", before, after, "--", "parents/*.md", "vendors/*.md")
    else:
        out = git("show", "--name-status", "--no-renames", "--format=", after, "--", "parents/*.md", "vendors/*.md")
    paths = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0] in ("A", "M"):
            paths.append(parts[1])
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="")
    ap.add_argument("--after", required=True)
    ap.add_argument("--paths", default="", help="post files to check instead of the ones the commits changed")
    ap.add_argument("--mode", choices=["live", "dry-run", "rehearsal"], default="live")
    ap.add_argument("--simulate-fail", action="store_true")
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = ap.parse_args()
    test_mode = args.mode != "live" or args.simulate_fail

    paths = args.paths.split() if args.paths.strip() else changed_posts(args.before, args.after)
    posts = [load_post(p) for p in paths]
    for p in posts:
        if p["draft"]:
            log(f"skip {p['path']}: draft: true")
    posts = [p for p in posts if not p["draft"]]
    if not posts:
        log("No added or changed posts to check.")
        return 0
    log(f"Checking {len(posts)} post(s) on {BASE_URL} as {' and '.join(USER_AGENTS)} "
        f"(title in <head> required: {REQUIRE_TITLE_IN_HEAD}; mode: {args.mode}"
        f"{'; simulated failure' if args.simulate_fail else ''})")
    run_checks(posts, args.simulate_fail, test_mode)

    failing = [p for p in posts if not p["ok"]]
    summary = [f"### Live check ({args.mode})", "", "| Post | Result |", "|---|---|"]
    summary += [f"| {p['slug']} | {'PASS' if p['ok'] else 'FAIL — ' + '; '.join(c['ua'] + ': ' + ', '.join(c['problems']) for c in p['checks'] if not c['ok'])} |" for p in posts]
    if not failing:
        log("All checked posts are live and readable by both crawlers.")
        write_summary(summary)
        return 0

    healthy, why = control_healthy({p["path"] for p in posts})
    log(f"Site health control: {'OK' if healthy else 'NOT OK'} — {why}")
    failing_paths = {p["path"] for p in failing}
    by_target: dict[str, list[dict]] = {}
    actions: dict[str, str] = {}
    for post in failing:
        if not healthy and args.mode != "rehearsal":
            actions[post["path"]] = f"not reverted: the site itself looks unhealthy ({why})"
            continue
        target, reason = decide(post, args.before, args.after, failing_paths, args.mode == "rehearsal")
        log(f"  {post['slug']}: {'REVERT — ' if target else 'no revert — '}{reason}")
        if args.mode == "rehearsal":
            # Rehearse the revert mechanics on a throwaway branch whatever the decision.
            by_target.setdefault("rehearsal", []).append(post)
        elif target:
            by_target.setdefault(target, []).append(post)
        else:
            actions[post["path"]] = f"not reverted: {reason}"
    for target, group in by_target.items():
        try:
            pr, result = revert(target, [p["slug"] for p in group], args.mode, args.run_id, [p["path"] for p in group])
        except Exception as err:  # a failed revert must still leave an issue behind
            pr, result = None, f"the revert could not be completed: {err}"[:600]
            cleanup_after_failure(args.mode, args.run_id)
        log(f"  {result}")
        for p in group:
            actions[p["path"]] = result if pr else f"not reverted: {result}"
    for post in failing:
        url = open_issue(post, actions[post["path"]], args.mode)
        log(f"  issue: {url}")
        log(f"::error title=Live check failed::{post['slug']}: {' '.join(actions[post['path']].split())}")
        summary.append(f"\n- **{post['slug']}**: {actions[post['path']]} — issue {url}")
    write_summary(summary)
    return 0 if test_mode else 1


def write_summary(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
