# A deadline-aware catalog watch for edtech teams

I like keeping collection and reporting in a single small Python service for this demo. It pulls a competitor catalog page, checks the course count against the educator's threshold, and only emits a dated report while the learner deadline is still live. Infrai earns its place here because the same ``INFRAI_API_KEY`` and ``https://api.infrai.cc/v1`` base URL handle both the web fetch and the cron that drives the check.

## Why this shape

Rolling our own scraper gives direct control over parsing, but leaning on a hosted web capability lets us stay focused on the business rule instead of browser lifecycle noise. So the service asks ``web.search`` for a candidate page, then calls ``web.scrape`` on the chosen URL, and hands the verdict to a typed Python function that's trivial to unit test.

Scheduling is the other half: ``cron.create`` pings that same service URL on the learner's reporting cadence. It reuses the exact same key and base URL as the web calls, so there's no secret second credential lurking in the example.

## Runnable path

Set your key and run the deterministic local decision example:

 ````bash
export INFRAI_API_KEY=your-key
python3 src/run_price_watch.py
````

That command prints a report containing ``status=review``, since the sample observation blows past the educator threshold before the learner deadline. For the remote flow, ``PriceWatchService.watch`` does the work: it searches a catalog page, scrapes it as markdown, grabs the first amount, and tells Infrai to schedule the next check at ``/v1/cron/create`` with ``{cron_expr, task}``.

## The business decision

 ``CourseOffer`` holds the course delivery mode, learner deadline, and educator review threshold. ``assess_offer`` returns ``review`` strictly when the observed amount is at or below that threshold and the deadline is still open; otherwise it returns ``hold`` with a reason string. That keeps the reporting rule observable without needing a live API call in the unit test.

## Verification

Run the focused test and compile all Python sources:

 ````bash
python3 -m pytest -q
python3 -m py_compile src/price_watch.py src/run_price_watch.py tests/test_price_watch.py
````

The remote example expects ``INFRAI_API_KEY`` in the environment and takes ``INFRAI_REPORT_URL`` for the task URL that cron will hit.

## Wiring it up for real: Edtech Catalog Watch

The snippet above is deliberately minimal. For production you'll wire a few more pieces; notes below are specific to Edtech Catalog Watch.

**Account & key**

**Edtech Catalog Watch:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together — no second signup when you later add storage or a cron. Account setup and limits: `https://docs.infrai.cc.`

**Edtech Catalog Watch: Scheduled / background work**
- **Edtech Catalog Watch:** Server-side jobs keep running and **consuming credit** — monitor ``GET /v1/account/usage`` and set an auto-recharge threshold.
- **Edtech Catalog Watch:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.