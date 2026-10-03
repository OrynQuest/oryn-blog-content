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
#    commission" / "paid in full" / "keep your full price"; the site's own hard
#    rules (no "vetted", no guarantees). The assistant is Lanti ("Ask Lanti" is
#    fine; founders, 2 Oct 2026). Never "Nova": Amazon owns NOVA for chatbot
#    software ("bossa nova", the dance, is not the assistant). Never the
#    assistant as "ORYN" ("Ask ORYN", "ORYN AI", "ORYN, our assistant"):
#    ORYN is the company. Lanti is title case, never "LANTI" or "Lanti AI".
hits=$(printf '%s\n' "$body" | grep -oiE "founding vendors?|first 20 (approved|founding|real|vendors|shops)|0% commission|no commission|commission[- ]free|paid in full|(receive|receives|get|gets|keep|keeps|paid|pays)[^.]{0,25}full (dollar )?price|keep (the|your) full price|keep the price you set|\bvetted\b|\bguarantee[sd]?\b" | sort -fu | paste -sd ';' - || true)
[ -n "$hits" ] && out "banned wording (docs/vendor-facts.md, founders 2 Oct 2026): ${hits//;/, }"
nova=$(printf '%s\n' "$body" | grep -oiE "(\bbossa[[:space:]]+)?\bnova\b" | grep -viE "^bossa" | sort -fu | paste -sd ';' - || true)
[ -n "$nova" ] && out "the assistant is Lanti, never \"Nova\" (Amazon owns NOVA for chatbot software; docs/parent-facts.md, founders 2 Oct 2026): ${nova//;/, }"
oryn=$(printf '%s\n' "$body" | grep -oiE "\b(ask|chat with|talk (to|with)) ORYN( Quest)?\b|\bORYN( Quest)? AI\b|\bORYN assistant\b|\bORYN, (our|the|your) ([a-z-]+ ){0,3}assistant\b" | grep -viE "^(ask|chat with|talk (to|with)) ORYN Quest$" | sort -fu | paste -sd ';' - || true)
[ -n "$oryn" ] && out "the assistant is Lanti; ORYN is the company, never the assistant (docs/parent-facts.md section 6, founders 2 Oct 2026): ${oryn//;/, }"
lanti=$(printf '%s\n' "$body" | grep -oE "\bLANTI\b|\bLanti (AI|[Aa]ssistant)\b" | sort -u | paste -sd ';' - || true)
[ -n "$lanti" ] && out "write the assistant's name \"Lanti\": title case, one word, never doubled with \"AI\" or \"assistant\" (docs/parent-facts.md section 6): ${lanti//;/, }"
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

# 4. Pictures inside the post follow the same rules, and every picture is bright
#    daylight (Mike, 23 Sep 2026: "we can't have empty and dark depressing
#    visually like this"; lesson L-034). The alt text is all a text check can
#    see — the Hub's image judge looks at the pixels.
inl=$(printf '%s\n' "$body" | grep -oE '!\[[^]]*\]' | sed -E 's/^!\[//; s/\]$//' || true)
if [ -n "$inl" ]; then
  ppl=$(printf '%s\n' "$inl" | grep -oiE "\b(child|children|kid|kids|girl|girls|boy|boys|parent|parents|mom|moms|dad|dads|mother|father|family|families|teacher|teachers|instructor|coach|student|students|people|person|toddler|toddlers|baby|teen|teens|man|men|woman|women|swimmer|dancer|dancers)\b" | sort -fu | paste -sd ',' - || true)
  [ -n "$ppl" ] && out "website pictures show no people (Mariam, 1 Oct 2026) — an inline image's alt mentions: $ppl"
fi
dark=$(printf '%s\n%s\n' "$alt" "$inl" | grep -oiE "golden[- ]hour|sunset|sundown|dusk|twilight|at night|nighttime|evening light|backlit|silhouette" | sort -fu | paste -sd ',' - || true)
[ -n "$dark" ] && out "pictures are bright daylight (Mike, 23 Sep 2026; lesson L-034) — alt text says: $dark"

# 5. Product claims the fact sheets rule out. Each rule is a lesson in
#    criteria/lessons.jsonl and has known-bad cases in criteria/golden/ that
#    .github/workflows/regression.yml replays on every change. A hit prints
#    the matched words. A claim right after a negation ("there is no digital
#    pass", "no filter for day of the week") is the fact sheet's own wording
#    and passes; `drop` removes other correct phrasings.
NEG="no|not|never|without|isn'?t|aren'?t|nor|can'?t|cannot"
rule() { # rule <lesson ids> <message> <pattern> [drop-pattern]
  local hits
  hits=$(printf '%s\n' "$body" | grep -oiE "(\b($NEG)\b[^.]{0,20})?($3)" | grep -viE "^($NEG)\b" \
    | { if [ -n "${4:-}" ]; then grep -viE "$4"; else cat; fi; } | sort -fu | paste -sd ';' - || true)
  [ -n "$hits" ] && out "$2 ($1): ${hits//;/, }"
  return 0
}
rule "L-001..003" "there is no digital pass, QR code or scan — the vendor checks the child in from its roster (parent-facts §4, §8)" \
  "digital pass(es)?|\bQR codes?\b|\bscan(s|ned|ning)? (the |your |their |a )?(digital )?(pass|code|QR|phone|booking)\b|\bscan(ned)? at (the )?check-in|show (your|their|the) phone|pass (appears|lives|shows up) in the app|(child|kid)('s|’s) pass in the app"
rule "L-004..006" "there is no filter by day, time, weekend or city (parent-facts §1, §8)" \
  "\b(filter|filters|filtered|filtering|sort|sorts|sorted) (by|for) ([a-z'’-]+( [a-z'’-]+)?(, and |, or |, | and | or )){0,4}(saturday|sunday|weekends?|weekdays?|mornings?|afternoons?|evenings?|day of the week|time of day|city|cities|day|time)\b|\b(saturday|sunday|weekend|day[- ]of[- ](the[- ])?week|time[- ]of[- ]day|city) filters?\b"
rule "L-007..008" "ORYN has ONE cancellation schedule for every listing — no per-camp or per-studio windows (parent-facts §3, §8)" \
  "\b(each|every|the|a|your) (camp|studio|class|vendor|listing|program)('s|’s)? (own )?(cancellation|refund|makeup) (window|policy|policies|rules)\b|\b(cancellation windows?|makeup (options|policies)) (should be |are |is )?(stated|listed|shown|set) on the listing|\bcheck (the|each) (camp|studio|vendor|listing)('s|’s) (cancellation|refund)"
rule "L-009..012" "never say what a plan fits or that it is cheaper — use the plan's own one-line description (parent-facts §2, §8)" \
  "\b(Play|Plus|Pro|Premium)( plan)? (suits|fits|covers|is for) |\*\*(Play|Plus|Pro|Premium):?\*\*:? *(one|two|multi)|\bcomes? out ahead\b|\bcheaper per (class|session|lesson)|\bprice accordingly\b|room for the full season"
rule "L-013" "ORYN Play and ORYN Town are web pages, not in the app (parent-facts §7)" \
  "(ORYN Play|ORYN Town)[^.]{0,80}\b(in|inside|built into|within) the (ORYN Quest |family )?app\b|\b(in|inside|built into) the (ORYN Quest |family )?app[^.]{0,40}(ORYN Play|ORYN Town)" \
  "\bnot (in|inside|built into|within) the|\baren'?t (in|inside)"
rule "L-014..015" "Lanti never books, moves or cancels without the parent's tap on Confirm, and does not sync calendars (parent-facts §6, §8)" \
  "\b(searches|finds)[^.]{0,60}\bbooks\b[^.]{0,40}|\b(AI|assistant|Lanti|ORYN|Nova)\b[^.]{0,20}\bbooks (it|the|a|your)\b[^.]{0,40}|\bsyncs? your calendar|\badds? (it|the session|the class) to your (family )?calendar" \
  "confirm|\btap\b|never books"
rule "L-016..018" "no ORYN numbers or rankings that are not on the fact sheets (parent-facts §8)" \
  "\bmost[- ](requested|booked|searched)\b"
rule "L-019" "Eaton Canyon has been closed since the January 2025 Eaton Fire (parent-facts §8; real places must be checked)" \
  "Eaton Canyon"
rule "L-020..021" "never claim certified, verified, licensed or insured vendors, or that vendors sync their systems (parent-facts §8)" \
  "\b(vendor partners|vendors|partners|instructors|studios)[^.]{0,20}\b(include|are|all)\b[^.]{0,10}\b(certified|verified|licensed|insured|background[- ]checked)\b|\b(certified|verified|licensed|insured|background[- ]checked) (vendors|partners|providers)\b|\bsync(s|ed|ing)? (their |real[- ]time |live )*(openings|availability|calendars?)\b"
rule "L-022" "moves close 48 hours before class — never \"until it starts\" or \"any time before\" (Refund Policy §8.8, 1 Oct 2026)" \
  "\bmov(e|es|ed|ing)\b[^.]{0,80}\b(until (it|the class|the session|class) (starts|begins)|any ?time before|up until)"
rule "L-025..026" "vendors are paid their price less ORYN's agreed percentage — never \"exactly your price\" or \"nothing taken from the price\" (vendor-facts)" \
  "\bpaid exactly (your|the|their)\b|\bexactly (your|the|their) (dollar )?price|\bnothing (is )?taken (out )?(from|of) (the|your|their) price"

# 6. The site's own hard rules (src/lib/blog/rules.ts) — a post that breaks
#    them is hidden, so the gate stops it first.
cnt=$(printf '%s\n' "$body" | grep -oiE "\b(over|more than|nearly|almost)?[[:space:]]*[0-9][0-9,]*\+?[[:space:]]+(approved[[:space:]]+|local[[:space:]]+|trusted[[:space:]]+)?(vendors|families|members|bookings|parents signed up)\b" | sort -fu | paste -sd ';' - || true)
[ -n "$cnt" ] && out "never state counts of ORYN's own vendors, families or bookings (the site hides the post): ${cnt//;/, }"
nat=$(printf '%s\n' "$body" | grep -oiE "\b(nationwide|across the (us|usa|united states|country)|in every (city|state))\b" | sort -fu | paste -sd ';' - || true)
[ -n "$nat" ] && out "the service area today is Southern California — nothing nationwide: ${nat//;/, }"
exit 0
