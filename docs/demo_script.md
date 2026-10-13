# Demo video script (2 minutes)

*A draft to put in your own words. About 280 spoken words (1.9 minutes at 150 words per
minute, which leaves about 10 seconds for clicks and pauses, so rehearse with a stopwatch). Structure from the PRD: problem (15 s), live
walkthrough (85 s), results and limits (20 s). Updated for the current layout: "Biggest alerts" cards
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

**0:00 to 0:15. The problem** (title card, or the map in the background)

> "A watch analyst has to notice what changes: protests flaring, fighting spreading. The signal is in
> open news, but it arrives as tens of thousands of machine-coded records a day, many duplicated,
> misplaced or wrong. They need three things: what is happening where, what is unusual, and how much
> to trust it."

**0:15 to 0:35. The page and the alerts** (Home, top of page)

> "This is Tripwire. It loads the public GDELT event feed every fifteen minutes; the header shows how
> fresh it is. These are the biggest alerts: countries whose count of distinct articles for a category
> is far above their own twenty-eight-day normal."

*On screen: point at "Last GDELT update"; sweep across the three cards; rest on the one you chose.*

**0:35 to 0:55. Alert to map** (click Show on map)

> "One click filters the map to that country and event type. Dots spread as you zoom, and size is how
> many sources reported it. Click one for who, where, what, and a link to the article. I never store
> article text."

*On screen: click Show on map; point at the sidebar filters that changed; zoom in once; click a dot;
show the detail panel.*

**0:55 to 1:25. Evidence** (Alerts tab)

> "The Alerts tab shows the articles behind an alert and how GDELT coded each one. That matters: my
> audit found about four in ten alerts false, mostly misread event types, so an analyst has to check.
> Alerts marked ongoing are the same story continuing, and were real less often, though on a small
> sample."

*On screen: select the row; Evidence appears; point at "Coded as" and the Story column; open one link
(do not read the article).*

**1:25 to 1:40. Trend, quality, export** (Trend tab, sidebar)

> "Trend charts thirty days against the threshold. A model trained on three hundred hand labels scores
> event quality, and this toggle hides the low ones. Any view exports to CSV."

*On screen: Trend chart; tick "Hide low-quality events" and show the count drop; (optional) click
Download CSV in the Events table tab without opening it.*

**1:40 to 2:00. Results and limits** (About tab, or a plain slide with these lines)

> "I audited fifty alerts by hand: sixty-one percent were real. The quality model ranks better than
> chance, but modestly. Four fixes that won on my development set failed on alerts I held back, so I
> left the detector alone and wrote that down. It is an aid, not a verdict: always open the article.
> The code and evaluation are open source."

*End on the repo link and the live URL.*

## If you still run over

1. Drop "Any view exports to CSV." and the optional CSV click (about 4 s).
2. Drop the ongoing sentence in Evidence (about 8 s).
3. Skip the zoom and dot click in the map step (about 8 s); keep the evidence step, it is the strongest.

## Checks after recording

- Every number you said matches `docs/evaluation.md`: 61%, 50 alerts, about 300 labels (312 exist; say
  "about three hundred"). Only quote the ongoing figures (43% against 72%) if you want to explain the
  sample: it is 50 alerts, so treat it as suggestive.
- No clock, token, path or verdict form you did not want visible.
- The alert you showed still exists in the evidence table (the cards move through the day).
- Add captions: it will be watched muted.
- Put the video link in the README and on the application.
