"""Synthetic Bedrock traffic, so the cost monitor has something real to watch.

This is not part of the digest. It exists because a monitor that watches
CloudWatch cannot be demonstrated against a repository that has never called a
model, and CloudWatch metrics in the `AWS/Bedrock` namespace are written by AWS
-- they cannot be backfilled or faked. The only way to have a week of history
is to spend a week making calls.

Labelled loudly as synthetic for the same reason it exists: usage that looks
organic but is not would be worse than no usage at all, because somebody would
eventually reason from it.

**What it costs.** A normal day is twelve calls of roughly 120 input and 40
output tokens against a 7B model, which is about $0.0004. A month of daily runs
including the anomalous days is under two cents. That number is small enough to
be worth stating precisely, because "it's cheap" is how recurring spend gets
approved without anybody knowing the figure.

**Why some days are deliberately wrong.** The monitor compares a day against
the median of the days around it, so it needs most days to be ordinary. Making
every day anomalous would move the baseline onto the anomaly and detect
nothing -- which is itself the failure mode worth understanding: a system whose
normal *is* the problem has no internal evidence that anything is wrong.

The two bad days model the two ways spend actually goes wrong in production:

    balloon   something got appended to every prompt -- retrieved context, a
              longer template, a history window that stopped being trimmed.
    collapse  the prompt builder returned early and the model got a bare
              title. Nothing raises, output still arrives, and the bill goes
              *down*, which is why a ceiling alarm never finds this one.

Usage:

    python tools/traffic.py                 # what today's date calls for
    python tools/traffic.py --mode balloon  # force one, for a demo
    python tools/traffic.py --dry-run       # print the plan, spend nothing
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from pathlib import Path

try:
    # Inside Lambda the package sits beside this file at the root of the zip.
    from digest import llm, summarize
except ImportError:  # a checkout, where it is under src/
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from digest import llm, summarize

# Twelve is enough that one outlier call cannot move the day's average, and
# few enough that the whole exercise stays under a cent a month.
CALLS_PER_DAY = 12

# Cost is reported rather than assumed. These are ca-central-1 on-demand rates
# for the model in llm.MODEL_ID; if that model changes these must too, which is
# why the assertion below fails loudly rather than quietly mispricing.
USD_PER_1K_IN = 0.00017
USD_PER_1K_OUT = 0.00023
PRICED_MODEL = "mistral.mistral-7b-instruct-v0:2"

# Real incident text, so the prompts vary the way real ones would. Identical
# prompts twelve times over would also invite caching somewhere in the path and
# stop measuring what it claims to measure.
INCIDENTS = [
    ("Checkout unavailable in eu-west-1",
     "Health checks failed for 11 minutes. Customers saw a 503 on the payment step."),
    ("Search results slow",
     "p95 latency went from 240ms to 3.1s after the index rebuild."),
    ("Password reset emails delayed",
     "Queue depth reached 40k. Delivery lagged by up to 25 minutes."),
    ("Duplicate charges on retry",
     "A client retry created a second authorisation for 340 orders."),
    ("Image uploads rejected",
     "Objects over 4MB failed with a signature mismatch after the SDK bump."),
    ("Stale inventory counts",
     "The replica fell 90 seconds behind and oversold two SKUs."),
]

# What gets appended on a balloon day. Roughly two thousand characters, which
# is the size a retrieved-context block or an untrimmed history window
# realistically reaches.
_LOG_NOISE = (
    "\n\nRecent log context:\n"
    + "\n".join(
        f"  2026-08-11T0{i}:14:2{i}Z gateway upstream=api-{i} status=503 "
        f"latency_ms={800 + i * 37} retries={i % 3} pool=saturated "
        f"trace=8f2a{i}c1d-4b7e-11ef-9c3a-0242ac1{i}0002"
        for i in range(9)
    )
    + "\n  (truncated, 214 further lines)\n"
)


def plan_for(day: dt.date) -> str:
    """Which kind of day this is.

    Driven by the date rather than by chance so that a run is reproducible and
    so the anomalies recur without anybody remembering to trigger them. The
    divisors keep roughly two thirds of any fortnight ordinary, which is what
    the monitor needs to have a baseline at all.
    """
    if day.day % 5 == 0:
        return "balloon"
    if day.day % 7 == 0:
        return "collapse"
    return "normal"


def prompt_for(mode: str, title: str, body: str) -> str:
    if mode == "balloon":
        return summarize.build_prompt(title, body + _LOG_NOISE)
    if mode == "collapse":
        # No preamble, no body: what the model gets when the template did not
        # load or a guard returned before the prompt was assembled.
        return f"Summarise: {title}"
    return summarize.build_prompt(title, body)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("auto", "normal", "balloon", "collapse"),
                    default="auto", help="default: whatever today's date calls for")
    ap.add_argument("--calls", type=int, default=CALLS_PER_DAY)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the estimate, call nothing")
    args = ap.parse_args(argv)

    if llm.MODEL_ID != PRICED_MODEL:
        print(f"llm.MODEL_ID is {llm.MODEL_ID} but the rates here are for "
              f"{PRICED_MODEL}. Update USD_PER_1K_* before trusting the "
              f"figures this prints.", file=sys.stderr)
        return 2

    today = dt.datetime.now(dt.timezone.utc).date()
    mode = plan_for(today) if args.mode == "auto" else args.mode
    print(f"{today}  mode={mode}  calls={args.calls}  "
          f"model={llm.MODEL_ID}  region={llm.AWS_REGION}")

    # Seeded from the date, so a rerun of the same day sends the same prompts
    # and a repeated run does not quietly change the day's average.
    rng = random.Random(today.toordinal())
    picks = [rng.choice(INCIDENTS) for _ in range(args.calls)]

    if args.dry_run:
        chars = sum(len(prompt_for(mode, t, b)) for t, b in picks)
        est_in = chars / 4
        print(f"  would send ~{int(est_in):,} input tokens, "
              f"about ${est_in / 1000 * USD_PER_1K_IN:.5f} of input")
        return 0

    sent = failed = 0
    for title, body in picks:
        try:
            llm.call(prompt_for(mode, title, body))
            sent += 1
        except Exception as e:  # noqa: BLE001 -- the reason is printed, not swallowed
            failed += 1
            print(f"  failed: {type(e).__name__}: {e}", file=sys.stderr)
            # Expired credentials fail every call identically; stopping after
            # the first keeps a broken schedule from producing a wall of the
            # same error every day.
            if failed >= 3:
                print("  three failures in a row, stopping", file=sys.stderr)
                break

    print(f"  sent {sent}, failed {failed}")
    # Non-zero when nothing got through, so a scheduled run that has quietly
    # stopped working shows up as a failure rather than as a silent gap.
    return 0 if sent else 1


def handler(event=None, context=None) -> dict:
    """One scheduled batch, run from Lambda.

    The mode comes from the EventBridge event rather than from the date. Two
    rules point here -- one for most days and one for the day that is
    deliberately wrong -- because a schedule that says which day is which is
    readable in the console, whereas a date arithmetic buried in this file is
    not, and somebody looking at an alert needs to be able to check whether it
    was the planted one.
    """
    mode = (event or {}).get("mode", "auto")
    if mode == "auto":
        mode = plan_for(dt.datetime.now(dt.timezone.utc).date())

    rng = random.Random(dt.datetime.now(dt.timezone.utc).date().toordinal())
    picks = [rng.choice(INCIDENTS) for _ in range(CALLS_PER_DAY)]

    sent = 0
    errors: list[str] = []
    for title, body in picks:
        try:
            llm.call(prompt_for(mode, title, body))
            sent += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")
            if len(errors) >= 3:
                break

    if not sent:
        # Raise rather than return quietly. A traffic generator that has
        # silently stopped leaves the monitor watching a flat line and
        # reporting that nothing is wrong, which is the same failure the
        # monitor itself is built to avoid.
        raise RuntimeError(f"no calls got through: {errors}")
    return {"mode": mode, "sent": sent, "failed": len(errors)}


if __name__ == "__main__":
    raise SystemExit(main())
