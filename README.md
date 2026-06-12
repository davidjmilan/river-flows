# New England River Flows

A static webpage (hostable on GitHub Pages) that shows current discharge in
cubic feet per second (CFS) for four paddling rivers in Massachusetts and
Connecticut, with a weekly flow graph for each. Tap a river's name to expand
its chart.

| River | Source | History |
| --- | --- | --- |
| Hoosic River | USGS gage 01332500 (live API) | Real 7-day, from USGS |
| Farmington River | USGS 01186000 **+** Still River 01186500, summed (live API) | Real 7-day, from USGS |
| Upper Deerfield (Fife Brook) | safewaters.com (scraped) | Built up by scheduled job |
| Dryway (Deerfield #5) | h2oline.com (scraped) | Built up by scheduled job |

## How it works

The two USGS-backed rivers are fetched live in the browser from the USGS Water
Services API, which serves CORS-enabled JSON including a full 7-day series.

The two Deerfield sections have **no public API and no historical feed** — each
source page publishes only a single current value. To build a real weekly
history, a GitHub Actions workflow (`.github/workflows/update-flows.yml`) runs
`scripts/scrape_deerfield.py` every hour, appends each reading to
`data/upper-deerfield.json` and `data/dryway.json`, prunes anything older than
8 days, and commits the files back to the repo. The webpage then loads those
files. The graphs therefore fill in over the first week after you deploy.

## Setup

1. Create a new GitHub repository and push these files to it (keep the layout).
2. **Enable write permission for Actions:** repo **Settings → Actions → General
   → Workflow permissions → Read and write permissions → Save.** The workflow
   needs this to commit the updated data files.
3. **Enable Pages:** **Settings → Pages → Build and deployment → Source: Deploy
   from a branch → Branch: `main` / root → Save.** Your site appears at
   `https://<user>.github.io/<repo>/`.
4. **Kick off the first scrape:** open the **Actions** tab, select *Update
   Deerfield flow history*, and click **Run workflow**. After it succeeds, the
   `data/*.json` files will hold their first reading. The job then runs
   automatically every hour.

That's it — no build step, no dependencies, no server.

## Notes & limitations

- **Scheduled runs can be delayed.** GitHub often defers `schedule` triggers by
  several minutes under load, and disables scheduled workflows on repos with no
  activity for 60 days. A commit or a manual run re-enables them.
- **Scrapers are brittle by nature.** If either source changes its page wording,
  the regex in `scrape_deerfield.py` may need a tweak. The script logs a
  warning and preserves existing history rather than failing the whole job.
- **Adjust frequency** by editing the `cron` line in the workflow. Hourly gives
  ~168 points per week — a smooth graph — while keeping committed files tiny.
  Actions are free and unlimited on public repos.
- **Time zones.** Stored timestamps are UTC (ISO 8601); the page renders them in
  the viewer's local time.

## Files

```
index.html                          the webpage
data/upper-deerfield.json           rolling history (Fife Brook)
data/dryway.json                    rolling history (Dryway / Deerfield #5)
scripts/scrape_deerfield.py         scraper run by the Action
.github/workflows/update-flows.yml  schedule + commit workflow
```
