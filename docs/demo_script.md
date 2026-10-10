# Demo video script (2 minutes)

*A draft to put in your own words. Roughly 300 spoken words. Structure from the PRD: problem
(20 s), live walkthrough (80 s), results and limits (20 s).*

## Before you record

- `make up` running; check the header says the data is a few minutes old (the worker is working).
- Use the live URL if Railway is up, otherwise `http://localhost:8501`.
- Browser at 1920x1080, zoom 100%, one tab, no bookmarks bar. Use light theme (the map and chart
  colours were checked for both, but light is the easiest to read on video).
- Sidebar: window "Last 24 hours", the five default categories, no countries chosen.
- **Do not** show the Label page, your `.env`, or any terminal with secrets.
- Rehearse once with a stopwatch. Record in one take if you can; a screen recorder plus your voice is enough.
- Pick the alert you will click **before** recording: open Alerts, choose a recent day, find one whose
  articles are clearly real, and note its country so you can find it fast.

## Script

**0:00 to 0:20. The problem** (face or title card, or the map in the background)

> "A regional watch analyst has to notice when something changes: protests flaring in a city, fighting
> spreading across a border. The raw signal exists in open news, but it arrives as tens of thousands of
> machine-coded records a day, and many are duplicated, misplaced or just wrong. They need three
> things fast: what is happening where, what is unusual, and how much to trust it."

**0:20 to 0:40. The map** (Home page)

> "This is Tripwire. It loads the public GDELT event feed every fifteen minutes. The header shows how
> old the data is. Each dot is a place and event type; colour is the category, size is how many
> sources reported it."

*On screen: point at the freshness number; hover a dot for the tooltip; click one dot.*

> "Click a dot and you get who, where, what, and a link to the source article. I never fetch article
> text; it links out."

**0:40 to 1:05. Alerts and evidence** (Alerts tab)

> "The Alerts tab ranks countries whose article count for a category is far above their own
> twenty-eight-day normal. I count distinct articles, not event rows, because one article can create
> several rows."

*On screen: select a row; the Evidence section appears; point at the 'Coded as' column.*

> "Select an alert and you see the articles behind it and how GDELT coded each. This matters because
> my audit found about four in ten alerts are false, mostly misread event types. Two or three clicks
> and an analyst can tell."

**1:05 to 1:25. Trend and quality** (Trend tab, then sidebar)

> "The Trend tab charts thirty days for that country, with the threshold and the flagged days. And a
> small model, trained on three hundred hand labels, scores each event's quality; this toggle hides
> the low ones."

*On screen: Trend tab shows the chart; back on Home tick "Hide low-quality events" and show the count drop.*

**1:25 to 1:40. Hand-off** (Events table)

> "Any filtered view exports to CSV for hand-off."

*On screen: click Download CSV (do not open the file).*

**1:40 to 2:00. Results and limits** (About tab, or a plain slide with these lines)

> "How well does it work? I audited fifty alerts by hand: sixty-one percent were real. The quality
> model ranks events better than chance, but modestly. Four fixes that looked good on my development
> set failed on the alerts I held back, so I left the detector alone and wrote that down. It is an aid
> for prioritising, not a verdict: always open the article. The code, tests and evaluation are open
> source."

*End on the repo link and the live URL.*

## Cut list if you run over

1. Drop the CSV line (saves 10 s).
2. Shorten the problem to two sentences.
3. Skip the hover on the dot.

## Checks after recording

- Every number you said matches `docs/evaluation.md` (61%, 50 alerts, 300 labels).
- No clock, token, or path you did not want visible.
- Add captions: it will be watched muted.
- Put the video link in the README and on the application.
