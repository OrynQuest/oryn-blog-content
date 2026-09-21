# ORYN Quest blog content

Markdown posts for **orynquest.com/blog**. Written and published by Agency Hub; rendered by the ORYN Quest site within a minute of a commit. Nothing here is code — the site owns the layout, structured data, sitemap, RSS and `llms.txt`.

## Layout

```
parents/<slug>.md      posts for parents  → https://orynquest.com/blog/<slug>
vendors/<slug>.md      posts for vendors  → https://orynquest.com/blog/<slug>
public/blog/<slug>.png hero image (1200×630) → served at https://orynquest.com/blog-assets/<slug>.png
```

The folder decides the audience. The file name is the slug: lowercase, hyphens, no dates. Slugs must be unique across both folders.

## Front-matter (the site's contract)

```yaml
---
title: "What age should kids start swim lessons?"     # required, ≤ 70 chars shown, ≤ 60 ideal
description: "…"                                      # required, 120–160 chars, the meta description
date: 2026-09-28                                      # required, YYYY-MM-DD (also accepted: publishedAt, published)
updated: 2026-09-28                                   # optional (also: updatedAt, lastUpdated)
author: "ORYN Quest Team"                             # optional; "Mariam", "Eliza", "Mike/Manvel" map to founder profiles
image: /blog/swim-lessons-what-age.png                # hero, 1200×630 PNG/JPG under public/blog/, file name = slug (also: heroImage, cover)
imageAlt: "…"                                         # what the picture actually shows — required when image is set
video: https://www.youtube.com/watch?v=XXXXXXXXXXX    # optional; a public/unlisted YouTube URL → embed under the hero + VideoObject schema
areas: [Orange County]                                # where the post is for (see Areas) — Southern California first
keyword: "swim lessons age"                           # optional target keyword (also: targetKeyword, keywords)
tags: [swimming, ages-3-5]                            # optional
answer: "…"                                           # optional 40–60-word direct answer shown under the title
canonical: https://…                                  # optional, only for syndicated posts
draft: false                                          # optional; true hides the post
---
```
Unknown keys are ignored. A post missing `title`, `description` or `date` is skipped by the site (and reported), never a build failure.

## Images and video (every post should have a hero image)
- **Hero image is expected on every post**: `public/blog/<slug>.png` (or .jpg/.webp), 1200×630, under 300 KB, relevant to the post (the activity, the space, the kit) — not a generic stock scene. The site uses it as the card image, the page hero, the Open Graph / share image and the `image` in the article's structured data.
- **Alt text describes the actual picture** (a parent reads it with a screen reader; Google reads it for image search). A post with an image and no alt text is published with the title as alt and flagged.
- **No photos of real children.** Generated or licensed imagery only; no logos or brand text in the frame; no swimwear scenes.
- Inline images in the body: standard Markdown `![alt](/blog-assets/<file>.png)` for files committed under `public/blog/`.
- **Video** is optional: set `video:` to a YouTube URL (public or unlisted). The site embeds it (privacy-enhanced, lazy) and emits `VideoObject` structured data with the post's title, description, date and thumbnail. Keep the transcript's key points in the body — search engines read text, not video.
- Without a hero, the card falls back to a branded cover generated from the title; the page shows no hero. So: always ship a hero.

## Areas (Southern California first — per post, never site-wide)
- `areas:` says where the post is for: `[Orange County]`, `[Los Angeles, Long Beach]`, or `[Southern California]` for a region-wide post. Recognised today: Southern California, Los Angeles, Glendale, Burbank, Orange County, San Diego, Inland Empire, Ventura County, Long Beach, Pasadena, Irvine, Anaheim, Santa Monica, Riverside, San Bernardino, Temecula (SoCal / LA / OC are understood). Any other place is kept as written — when ORYN expands, write it as one list item `"City, State"` (e.g. `["Phoenix, Arizona"]`); no site change is needed.
- The site turns `areas` into location chips on the post and the card, `<meta keywords>`, RSS categories, and `spatialCoverage` / `contentLocation` in the article's structured data. The area never appears on the site's main landing page or in the site-wide Organization schema — the founders will expand, and the blog is where the local page lives.
- Editorial: put the area in the keyword and the title when a family would search that way ("swim lessons in Orange County", "kids' art classes in Pasadena"); name real local specifics (seasons, school calendars, venue types, drive times); keep one evergreen post for every two or three local ones. A local post is still about the activity — the area is not padding, and never claims "best in …".

## Body conventions the site understands
- Standard Markdown (GitHub-flavoured: tables, task lists, footnotes).
- A `## FAQ` section whose items are `### Question?` followed by the answer becomes an FAQ block with `FAQPage` structured data. The FAQ ends at the next `##` heading or at a `---` line — put a `---` before any closing call-to-action paragraph so it is not read as part of the last answer.
- `> **Key takeaways**` blockquote at the top renders as a callout.
- Links to `/explore`, `/waitlist`, `/vendors` are the calls to action; the site adds an audience button at the end regardless.

## Rules the site enforces (a post breaking a hard rule is hidden until fixed)
- The word for a business on ORYN Quest is **vendor**, never "provider".
- Never "vetted", never counts of vendors/families/bookings, never guarantees.
- No photos of real children. Informational only on health/therapy topics.
- Service area today is Southern California; a post says which area it covers (`areas:`) rather than implying nationwide coverage.

_Site loader verified live on 20 Sep 2026 (push webhook → orynquest.com/api/blog/revalidate)._

## How a post goes live (Agency Hub → this repo → orynquest.com)
1. Agency Hub publishes an approved piece as a **pull request** from its `AceWattGit` account on a branch `agencyhub/<slug>` (one Markdown file + the hero under `public/blog/`).
2. `.github/workflows/auto-merge-agencyhub.yml` merges it automatically when the change is only files under `parents/`, `vendors/` or `public/blog/`, added or modified, with `title`, `description` and `date` in the front-matter and a valid slug. Anything else stays open and the workflow comments why.
3. The push to `main` calls the site's revalidate webhook; the post is live within a minute. A post that breaks an editorial hard rule (see above) is hidden by the site until fixed.

The founders' review happens inside Agency Hub before step 1; the pull request is a technical step, not a second review.
