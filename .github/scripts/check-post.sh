#!/usr/bin/env bash
# The founders' copy rules and the site's SEO limits for ONE post file.
# Prints one problem per line ("- <file>: …"); prints nothing when the post is fine.
# Used by auto-merge-agencyhub.yml on every Agency Hub pull request, and runnable
# by hand: .github/scripts/check-post.sh vendors/my-post.md [shown-name]
# Sources: docs/vendor-facts.md, docs/parent-facts.md, README.md (front-matter
# contract), and the site's src/lib/blog/rules.ts. Set up 2 Oct 2026 (QUEST).
set -uo pipefail
path="$1"; name="${2:-$1}"
body=$(cat "$path")
fm=$(printf '%s\n' "$body" | awk 'NR==1 && $0!="---" {exit} NR>1 && /^---$/ {exit} NR>1 {print}')
fmv() { printf '%s\n' "$fm" | sed -nE "s/^$1:[[:space:]]*//p" | head -1 | sed -E 's/[[:space:]]+#.*$//; s/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'; }
out() { printf -- '- %s: %s\n' "$name" "$1"; }

# 1. Wording the founders ruled out on the public site (2 Oct 2026): the founding
#    offer is never published; ORYN keeps an agreed percentage, so no "no
#    commission" / "paid in full" / "keep your full price"; the assistant is Nova;
#    the site's own hard rules (no "vetted", no guarantees).
hits=$(printf '%s\n' "$body" | grep -oiE "founding vendors?|first 20 (approved|founding|real|vendors|shops)|0% commission|no commission|commission[- ]free|paid in full|(receive|receives|get|gets|keep|keeps|paid|pays)[^.]{0,25}full (dollar )?price|keep (the|your) full price|keep the price you set|ORYN AI|ORYN assistant|Ask ORYN|\bvetted\b|\bguarantee[sd]?\b" | sort -fu | paste -sd ';' - || true)
[ -n "$hits" ] && out "banned wording (docs/vendor-facts.md, founders 2 Oct 2026): ${hits//;/, }"
prov=$(printf '%s\n' "$body" | grep -oiE "([a-z-]+[[:space:]]+)?providers?\b" | grep -viE "^(insurance|oauth|sign-in|login|identity|email|internet|health ?care|healthcare|therapy|service)[[:space:]]+providers?$" | sort -fu | paste -sd ';' - || true)
[ -n "$prov" ] && out "the word is \"vendor\", never \"provider\": ${prov//;/, }"

# 2. Search-result limits (README contract; the site's audit fails outside them).
title=$(fmv title); seo=$(fmv seoTitle); [ -z "$seo" ] && seo=$(fmv seo_title); [ -z "$seo" ] && seo=$(fmv metaTitle)
eff="${seo:-$title}"
[ "${#eff}" -gt 60 ] && out "search title is ${#eff} characters (max 60) — shorten the title or add seoTitle"
desc=$(fmv description)
if [ -n "$desc" ] && { [ "${#desc}" -lt 120 ] || [ "${#desc}" -gt 160 ]; }; then out "description is ${#desc} characters (must be 120–160)"; fi

# 3. Hero picture: real alt text, and no people on the website (Mariam, 1 Oct 2026).
img=$(fmv image); alt=$(fmv imageAlt)
if [ -n "$img" ]; then
  if [ -z "$alt" ]; then out "imageAlt is required when image is set";
  else
    printf '%s' "$alt" | grep -qiE "^hero image" && out "imageAlt must say what the picture shows, not \"Hero image: …\""
    ppl=$(printf '%s' "$alt" | grep -oiE "\b(child|children|kid|kids|girl|girls|boy|boys|parent|parents|mom|moms|dad|dads|mother|father|family|families|teacher|teachers|instructor|coach|student|students|people|person|toddler|toddlers|baby|teen|teens|man|men|woman|women|swimmer|dancer|dancers)\b" | sort -fu | paste -sd ',' - || true)
    [ -n "$ppl" ] && out "website pictures show no people (Mariam, 1 Oct 2026) — imageAlt mentions: $ppl"
  fi
fi
exit 0
