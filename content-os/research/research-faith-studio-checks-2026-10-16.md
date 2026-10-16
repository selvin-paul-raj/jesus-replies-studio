---
title: "Faith Studio (Jesus Replies) — helplines, Trial Reels, YouTube policy wording"
date: 2026-10-16
owner: Research Team (CRO)
requested_by: CEO 16:45 IST for Faith Studio (5371dbb4), due 20:00 IST
---

# Faith Studio checks — 16 Oct 2026

## 1. Crisis helplines (official pages, fetched 16 Oct 2026)
| Country | Line | Number | Hours | Source |
|---|---|---|---|---|
| US | 988 Suicide & Crisis Lifeline | **Call or text 988**, chat at chat.988lifeline.org | 24/7/365, free, confidential | https://988lifeline.org/ |
| UK & Ireland | Samaritans | **116 123** (free from any phone); Welsh line 0808 164 0123 | 24/7 | https://www.samaritans.org/how-we-can-help/contact-samaritan/ |
| India | Tele-MANAS (Ministry of Health) | **14416** or **1-800-891-4416** (toll-free) | 24/7 | https://telemanas.mohfw.gov.in/home |
| Philippines | NCMH Crisis Hotline (National Center for Mental Health) | **1553** (nationwide landline, toll-free) or **1800-1888-1553**; Smart/TNT 0919-057-1553; Globe/TM 0917-899-8727 / 0966-351-4518 | 24/7 | https://ncmh.gov.ph/contact-us (site blocked automated fetch; numbers match NCMH contact page in search, PIA govt news Oct 2025 https://pia.gov.ph/news/doh-mental-health-programs-crisis-hotlines-available-this-undas/ and BusinessWorld 2 Jul 2026) |
| Nigeria | **No national government suicide line.** Use: Lagos Lifeline (Lagos State Ministry of Health, open to anyone in Nigeria) | **070 0000 6463** or 020 1410 6463 (toll-free); WhatsApp 090 9000 6463 | 24/7 | https://lagosmind.org/lagos-lifeline |
| Nigeria (alt) | SURPIN (Suicide Research & Prevention Initiative) | **0800 078 7746** (+234-8000787746); also +234-908-021-7555, +234-903-440-0009 | site says 24/7 toll-free helpline | https://www.surpinng.com/ |
| Nigeria emergency | National emergency | 112 | — | lagosmind.org emergency guidance |

Notes: "No national Nigerian line" per TherapyRoute (checked Sep 2026, secondary) — consistent with no government line found. For a global audience, findahelpline.com (IASP) lists other countries.

## 2. Does Buffer support Instagram Trial Reels? — **Yes, since 7 Oct 2026 (in the Buffer app/composer).**
- Buffer changelog 7 Oct 2026: "Schedule trial reels: Share a reel with people who don't follow you yet…" — https://buffer.com/changelog/music-collaborators-and-more-for-instagram
- Buffer Help: Reel composer → Trial Reel **Off / Auto** (shows to followers after 72 h if it performs well) **/ Manual**. Needs a Professional (Business/Creator) account; you must confirm the Trial toggle exists in the Instagram app; can't combine with collaborators; **if the account doesn't meet Instagram's follower requirement, the post fails** with "account does not meet its follower requirement". — https://support.buffer.com/articles/scheduling-instagram-posts-reels-stories-and-notifications-3XA98S9Q5p
- ⚠️ **Buffer's public GraphQL API does not expose a trial-reel field today** (schema check 16 Oct: InstagramPostMetadataInput = firstComment, geolocation, isAiGenerated, link, shouldShareToFeed, stickerFields, type). So Faith Studio's API-based auto-publishing can't set Trial Reels yet; only the Buffer web/mobile composer can. (Our own schema introspection, not a Buffer statement.)
- Older Buffer help text still says "Trial reels are not supported" (outdated page version) — the newer article above supersedes it.

## 3. Does an account with 68 followers get Trial Reels? Is the 200-follower rule real? — **No at 68; yes, 200 is Instagram's official rule.**
- Instagram Help Center (US English): "you'll need a public Instagram account… If you have a **professional (business or creator) account, you must have at least 200 followers**. If you have a personal account, you must have at least 1,000 followers." Also: if the account is ineligible to appear in recommendations, it loses Trial Reels. — https://help.instagram.com/1013292530224018
- So @jesusrepliesofficial at 68 followers needs **132 more** (and a public professional account in good standing / recommendation-eligible) before Trial Reels will work; Buffer will fail the post until then.
- Caveats: the UK-English version of the same page still only says "professional account" (no number) — https://help.instagram.com/1013292530224018/?locale=en_GB; several schedulers (Post Bridge, PostFast, RecurPost) still quote 1,000 — outdated. Rollout can lag even after 200; the Trial toggle in the app is the final check (Planable help).

## 4. YouTube "Generic or Repetitive Content" wording — **Confirmed on the live Help page.**
Source: YouTube channel monetization policies — https://support.google.com/youtube/answer/1311392?hl=en (fetched 16 Oct 2026). Secondary dating: reorganised into named sections in **July 2026** (Tubefilter/TechCrunch via livereacting.com; techdogs.com says 16 Jul 2026; peggyktc.com 16 Jul 2026). The page's own dated note still reads 15 Jul 2025 (rename to "inauthentic content").
Exact wording:
> **Generic or Repetitive Content** — "Generic or repetitive content includes content that looks like it's made with a template, or that may feel repetitive to viewers after watching several videos in a row from the same channel."
> Allowed: "the substance of each video should be materially varied and deliver creative, educational, or other value" — e.g. "Same intro and outro for your videos, but the bulk of your content is different"; "a series following a set of characters across episodes… in which each video has a distinct storyline, focus, or concept".
> Not allowed (examples): "Similar or repetitive content with low educational value, commentary, narratives, or minimal variation across videos"; "Videos where characters are put in the same situation over and over again with the same outcome (i.e., using a highly similar storyline template across multiple videos)"; "Image slideshows, templated storylines, or scrolling text with minimal or no narrative, commentary, or educational value"; "AI-generated content made with generic or unoriginal templates giving the impression of mass production without adding the creator's original, authentic insights or perspective."
Same page also has **"Unsatisfying or Off-putting Content"** ("relies heavily on emotionally manipulative formulas… videos feel interchangeable") and **"AI Personas Related to Sensitive Topics"** (AI persona posing as a human expert on health/legal/finance/politics can't monetize).
**Relevance to Jesus Replies (inferred):** a fixed "question → Jesus answers" template is OK only if each episode has a distinct question, story and real substance; avoid identical storyline/outcome every time, emotional-manipulation formulas, and slideshow/scrolling-text episodes. The crisis/mental-health topics need helpline info, not advice framed as an expert persona.
