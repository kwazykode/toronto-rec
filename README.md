# Toronto Rec Tracker

A dependency-free tracker for published adult 19+ pickleball, volleyball, and badminton drop-in sessions at:

- Canoe Landing Community Recreation Centre
- One Yonge Community Recreation Centre

The interface follows the compact, single-file style of `atla-trivia` and `speedrun-cs-tracker`.

## Included schedule

- 110 adult 19+ sessions from July 20 through August 23, 2026
- City of Toronto data retrieved July 31, 2026
- July 20–26 uses the same recurring times as the published following weeks
- Multi-select filters for centre, sport, week, access type, and tracking status
- Mobile-friendly filter scrolling, tap targets, cards, and overview layout
- Date, time, centre, sport, and verified access labels replace repeated row titles
- Each week ends with its attended total for cost tracking
- One-click attended toggle
- Location-specific official City schedule link on every session
- Six-month pass tracker using a $159.80 paid cost, with live sessions-played
  and cost-per-session calculations
- Unlimited break-even bar targeting $4.96 per session at 33 attended sessions;
  100% sits at the 8/10 marker and higher progress continues in the final fifth
- Browser `localStorage` persistence

Schedules may change. Confirm sessions using the official City of Toronto drop-in sports map before attending.

Access labels come from the City sports map's `res` field. Canoe Landing uses
Reserve access for badminton and volleyball, offers both reservation and drop-in
inventory for Tuesday/Wednesday pickleball, and lists Thursday pickleball as
Drop-in Only. One Yonge sessions are listed as Drop-in Only.

## Run

Open `index.html` directly in a browser. No build or dependencies are required.

To add another recurring schedule week, append an entry to `WEEKS` in
`index.html`. Session totals, sport counts, week filters, and the tracked-week
summary update automatically.
