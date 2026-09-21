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
image: /blog/swim-lessons-what-age.png                # optional hero; a path under public/ (also: heroImage, cover)
imageAlt: "…"                                         # required when image is set
keyword: "swim lessons age"                           # optional target keyword (also: targetKeyword, keywords)
tags: [swimming, ages-3-5]                            # optional
answer: "…"                                           # optional 40–60-word direct answer shown under the title
canonical: https://…                                  # optional, only for syndicated posts
draft: false                                          # optional; true hides the post
---
```
Unknown keys are ignored. A post missing `title`, `description` or `date` is skipped by the site (and reported), never a build failure.

## Body conventions the site understands
- Standard Markdown (GitHub-flavoured: tables, task lists, footnotes).
- A `## FAQ` section whose items are `### Question?` followed by the answer becomes an FAQ block with `FAQPage` structured data. The FAQ ends at the next `##` heading or at a `---` line — put a `---` before any closing call-to-action paragraph so it is not read as part of the last answer.
- `> **Key takeaways**` blockquote at the top renders as a callout.
- Links to `/explore`, `/waitlist`, `/vendors` are the calls to action; the site adds an audience button at the end regardless.

## Rules the site enforces (a post breaking a hard rule is hidden until fixed)
- The word for a business on ORYN Quest is **vendor**, never "provider".
- Never "vetted", never counts of vendors/families/bookings, never guarantees.
- No photos of real children. Informational only on health/therapy topics.
- Service area today is Southern California; say so rather than implying nationwide coverage.

_Site loader verified live on 20 Sep 2026 (push webhook → orynquest.com/api/blog/revalidate)._
