# Toronto Rec Tracker

Mobile attendance and pass-cost tracker for 19+ pickleball, badminton, and
volleyball at five downtown Toronto community centres.

[Open tracker](https://kwazykode.github.io/toronto-rec/)

## Features

- Historical sessions since July 20, 2026
- Weekly City schedule previews
- Centre, sport, week, day, access, and attendance filters
- $159.80 pass analysis with a $4.96 per-session target
- Device-local attendance storage
- City schedule links and verified access labels

- Confirm current City details before attending.

## Weekly schedule updates

- Thursday 5:48 p.m.: check Toronto Open Data
- Retry at 5:58 p.m., then every 20 minutes until the fetch succeeds
- Stop after the 8:18 p.m. attempt if the City data remains unavailable
- Create a review issue and downloadable preview
- Commit nothing during the preview step
- Run **Apply weekly schedule preview** with the approved run ID
- Review and merge its pull request to publish
- Uses free public-repository GitHub Actions and GitHub Pages

## Development

- Open `index.html`; no build dependencies
- Refresh data: `python3 scripts/update_schedule.py`
- Test: `python3 -m unittest discover -s tests -v`
- Search indexing is disabled; the public URL still works
