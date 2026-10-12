# Demo video script (2 minutes)

*A draft to put in your own words. About 345 spoken words (roughly 2.3 minutes at 150 words per
minute, so speak briskly or use the cut list). Structure from the PRD: problem (20 s), live
walkthrough (80 s), results and limits (20 s). Updated for the current layout: "Biggest alerts" cards
above the map, Show on map, the Story column, and the shorter tables.*

## Before you record

- `make up` running; check the header says the data is a few minutes old (the worker is working).
- Use the live URL if Railway is up, otherwise `http://localhost:8501`.
- **Hide the verdict form.** On your machine the Alerts tab shows "Your verdict on this alert"
  because labeling is switched on locally. Either record on the live URL (where it is off), or stop the
  app and start it without `ENABLE_LABELING`, or just do not scroll below the evidence table.
- Browser at 1920x1080, zoom 100%, one tab, no bookmarks bar. Light theme (easiest to read on video).
- Sidebar at its defaults: window "Last 24 hours", the five default categories, no countries chosen.
  (A clean link to start from: the plain URL with nothing after it.)
- **Do not** show the Label page, your `.env`, or any terminal with secrets.
- Rehearse once with a stopwatch. One take if you can; a screen recorder plus your voice is enough.
- **Pick the alert before recording.** Look at the three "Biggest alerts" cards. Choose one whose
  articles are clearly real (open the evidence once off camera) and one with a "new" story marker. The
  cards change as the day goes on, so choose within an hour of recording.
- Click "Show on map" once as a rehearsal, then clear the Countries and Categories filters (or reload)
  so the take starts from the default view.

## Script

**0:00 to 0:20. The problem** (title card, or the map in the background)

> "A regional watch analyst has to notice when something changes: protests flaring in a city, fighting
> spreading across a border. The raw signal exists in open news, but it arrives as tens of thousands of
> machine-coded records a day, and many are duplicated, misplaced or just wrong. They need three
> things fast: what is happening where, what is unusual, and how much to trust it."

**0:20 to 0:45. The page and the alerts** (Home, top of page)

> "This is Tripwire. It loads the public GDELT event feed every fifteen minutes, and the header shows
> how old the data is. Under it are the biggest alerts: countries whose article count for a category is
> far above their own twenty-eight-day normal. I count distinct articles, not event rows, because one
> article can create several rows."

*On screen: point at "Last GDELT update"; sweep across the three alert cards; read one sentence aloud.*

**0:45 to 1:05. Alert to map** (click Show on map)

> "One click filters the map to that country and event type. Dots stay put as you zoom, so they spread
> apart, and size is how many sources reported it."

*On screen: click Show on map on the alert you chose; point at the sidebar filters that changed;
scroll up if needed; zoom in once; click a dot; show the detail panel and the "Open source article" link.*

> "Click a dot and you get who, where, what, and a link to the source article. I never fetch article
> text; it links out."

**1:05 to 1:30. Evidence** (Alerts tab)

> "In the Alerts tab, select the alert and you see the articles behind it and how GDELT coded each one.
> This matters because my audit found about four in ten alerts are false, mostly misread event types, so
> an analyst needs to check. Alerts marked ongoing are the same story continuing; in my audit those
> were real less often, though that is a small sample."

*On screen: select the row; the Evidence section appears; point at the "Coded as" column and the
Story column; open one article link (do not read the article).*

**1:30 to 1:45. Trend, quality and hand-off** (Trend tab, sidebar, Events table)

> "The Trend tab charts thirty days against the threshold. A small model, trained on three hundred hand
> labels, scores each event's quality, and this toggle hides the low ones. Any filtered view exports
> to CSV."

*On screen: Trend tab shows the chart; tick "Hide low-quality events" and show the count drop; Events
table tab; click Download CSV (do not open the file).*

**1:45 to 2:00. Results and limits** (About tab, or a plain slide with these lines)

> "How well does it work? I audited fifty alerts by hand: sixty-one percent were real. The quality
> model ranks events better than chance, but modestly. Four fixes that looked good on my development
> set failed on the alerts I held back, so I left the detector alone and wrote that down. It is an aid
> for prioritising, not a verdict: always open the article. The code, tests and evaluation are open
> source."

*End on the repo link and the live URL.*

## Cut list if you run over (the four cuts save about 33 seconds)

1. Drop the CSV line (saves 5 s).
2. Drop the "ongoing" sentence in the Evidence section (saves 10 s).
3. Shorten the problem to two sentences (saves 8 s).
4. Skip the zoom and dot click (saves 10 s); keep the evidence step, it is the strongest part.

## Checks after recording

- Every number you said matches `docs/evaluation.md`: 61%, 50 alerts, about 300 labels (312 exist; say
  "about three hundred"). Only quote the ongoing figures (43% against 72%) if you want to explain the
  sample: it is 50 alerts, so treat it as suggestive.
- No clock, token, path or verdict form you did not want visible.
- The alert you showed still exists in the evidence table (the cards move through the day).
- Add captions: it will be watched muted.
- Put the video link in the README and on the application.
